from funcy import group_by, cached_property, partial, walk_keys, lmap, first, where
from datatableview.views import DatatableView
from datatableview.utils import DatatableOptions
from handy.decorators import render_to, paginate
from handy.utils import get_or_none

from django.db import transaction
from django.http import HttpResponseForbidden, Http404
from django.forms import ModelForm, CharField
from django.shortcuts import get_object_or_404, redirect

from tags.models import SeriesAnnotation, SampleAnnotation, RawSeriesAnnotation, RawSampleAnnotation
from .annotate_core import calc_validation_stats, update_canonical


class AnnotationsSearchOptions(DatatableOptions):
    def _normalize_options(self, query, options):
        """
        Here we parse some search tokens diffrently to enable filtering:
            GSE\d+ and GPL\d+    filter by specific serie or platform
            tag=\w+              filters by tag
            valid                selects validated annotations
        """
        options = DatatableOptions._normalize_options(self, query, options)
        # Try normally named field
        if not options['search']:
            options['search'] = query.get('search', '').strip()

        filters = group_by(r'^(GSE|GPL|[Tt]ag=|valid|novalid)', options['search'].split())
        options['search'] = ' '.join(filters.pop(None, []))

        filters = walk_keys(str.lower, filters)
        filters['tag'] = lmap(r'^[Tt]ag=(.*)', filters.pop('tag=', []))
        options['filters'] = filters

        return options


class SeriesAnnotations(DatatableView):
    model = SeriesAnnotation
    template_name = 'tags/reviews/series.j2'
    datatable_options = {
        'columns': [
            'id',
            ('Series', 'series__gse_name'),
            ('Platform', 'platform__gpl_name'),
            ('Tag', 'tag__tag_name'),
            'samples',
            'annotations',
            'authors',
            'fleiss_kappa',
            'best_cohens_kappa',
        ],
        'search_fields': ['tag__description', ],
    }
    datatable_options_class = AnnotationsSearchOptions

    def get_queryset(self):
        return SeriesAnnotation.objects.filter(is_active=True) \
                                       .select_related('series', 'platform', 'tag')

    def apply_queryset_options(self, queryset):
        options = self._get_datatable_options()

        if options['filters']['gse']:
            queryset = queryset.filter(series__gse_name__in=options['filters']['gse'])
        if options['filters']['gpl']:
            queryset = queryset.filter(platform__gpl_name__in=options['filters']['gpl'])
        if options['filters']['tag']:
            queryset = queryset.filter(tag__tag_name__in=options['filters']['tag'])
        if options['filters']['valid']:
            queryset = queryset.filter(best_cohens_kappa=1)
        if options['filters']['novalid']:
            queryset = queryset.exclude(best_cohens_kappa=1)

        return super(SeriesAnnotations, self).apply_queryset_options(queryset)

    def get_context_data(self, **kwargs):
        context = super(SeriesAnnotations, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            context['snapshot'] = get_or_none(Snapshot, author=self.request.user, frozen=False)
        return context

series_annotations = SeriesAnnotations.as_view()


class SampleAnnotations(DatatableView):
    model = SampleAnnotation
    template_name = 'tags/reviews/samples.j2'
    datatable_options = {
        'columns': [
            ('Sample', 'sample__gsm_name'),
            'annotation',
        ]
    }

    def get(self, request, series_annotation_id):
        self.series_annotation = get_object_or_404(
            SeriesAnnotation.objects.select_related('series'),
            pk=series_annotation_id
        )
        return super(SampleAnnotations, self).get(request, series_annotation_id)

    @cached_property
    def sources(self):
        return list(self.series_annotation.raw_annotations.filter(is_active=True).order_by('id'))

    def get_queryset(self):
        return SampleAnnotation.objects.select_related('sample') \
                               .filter(series_annotation=self.series_annotation)

    def get_context_data(self, **kwargs):
        context = super(SampleAnnotations, self).get_context_data(**kwargs)
        context['series_annotation'] = self.series_annotation
        context['source_ids'] = [s.id for s in self.sources]
        return context

    def _get_datatable_options(self):
        options = super(SampleAnnotations, self)._get_datatable_options()
        options['columns'] = [col for col in options['columns']
                              if not isinstance(col, tuple) or col[1] is not None]
        options['columns'].extend(
            (self.get_source_title(src), None, partial(self.get_extra, src))
            for src in self.sources
        )
        return options

    @staticmethod
    def get_source_title(src):
        if src.created_by:
            return '%s %s' % (src.created_by.first_name, src.created_by.last_name)
        else:
            return '?'

    def get_extra(self, src, instance, *args, **kwargs):
        if not hasattr(self, 'extra_data'):
            qs = RawSampleAnnotation.objects.filter(series_annotation__in=self.sources)
            self.extra_data = {
                (anno_id, sample_id): annotation
                for anno_id, sample_id, annotation
                in qs.values_list('series_annotation', 'sample_id', 'annotation')
            }
        return self.extra_data[src.pk, instance.sample_id] or ''

sample_annotations = SampleAnnotations.as_view()


def ignore(request, series_annotation_id):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    with transaction.atomic():
        annotation = get_object_or_404(RawSeriesAnnotation.objects.select_for_update(),
                                       pk=series_annotation_id)
        annotation.ignored = True
        annotation.is_active = False
        annotation.save()

        # Recalc this and all subsequent raw annotations, update canonical
        raw_annotations = annotation.canonical.raw_annotations.filter(pk__gte=annotation.pk)
        for raw_annotation in raw_annotations:
            calc_validation_stats(raw_annotation)
        update_canonical(annotation.canonical_id)

    if annotation.canonical.is_active:
        return redirect('sample_annotations', annotation.canonical_id)
    else:
        return redirect('series_annotations')


# Snapshots

import urllib.request, urllib.parse, urllib.error  # noqa
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from tags.models import Snapshot


@login_required
@require_POST
def snapshot(request):
    action = request.POST.get('action')
    search = request.POST.get('search')
    next_url = '%s?%s' % (request.POST.get('next'), urllib.parse.urlencode({'search': search}))

    if action not in {'make', 'add', 'remove', 'delete', 'freeze'}:
        return HttpResponseForbidden('Unknown action %s' % action)

    if action == 'make':
        snap, _ = Snapshot.objects.get_or_create(author=request.user, frozen=False)
        messages.success(request, "Created an empty snapshot for you. "
                                  "Now add searches to it.")
        return redirect(next_url)

    snap = get_or_none(Snapshot, author=request.user, frozen=False)
    if not snap:
        return HttpResponseForbidden('No unfrozen snapshot found')

    if action == 'add':
        if not search:
            messages.error(request, "Can't add all the annotations to snapshot. "
                                    "Make some search or go into any annotation.")
        else:
            added, message = snap.add(search, get_search_qs(request))
            if added:
                snap.save()
                messages.success(request, 'Added "%s" to snaphot' % search)
            else:
                messages.warning(request, message)
    elif action == 'remove':
        removed, message = snap.remove(search)
        if removed:
            snap.save()
        elif message:
            messages.error(request, message)
    elif action == 'delete':
        snap.delete()
    elif action == 'freeze':
        snap.freeze()
        return redirect('snapshot_detail', snap.id)

    return redirect(next_url)


def get_search_qs(request):
    view = SeriesAnnotations()
    view._datatable_options = view.datatable_options_class(
        view.get_model(), request.POST,
        **SeriesAnnotations.datatable_options)
    view.request = request
    qs = view.get_object_list()
    return qs


class ReviewSnapshot(SeriesAnnotations):
    template_name = 'snapshots/review.j2'

    def get_queryset(self):
        snapshot = get_or_none(Snapshot, author=self.request.user, frozen=False)
        if not snapshot:
            return SeriesAnnotation.objects.none()
        return super(ReviewSnapshot, self).get_queryset() \
                                          .filter(id__in=snapshot.metadata.get('ids', []))
review_snapshot = login_required(ReviewSnapshot.as_view())


@render_to('snapshots/detail.j2')
def snapshot_detail(request, snap_id):
    snap = get_object_or_404(Snapshot, pk=snap_id)
    if not snap.frozen:
        if snap.author == request.user:
            return redirect('review_snapshot')
        else:
            raise Http404
    form = None

    if snap.author == request.user:
        if request.method == 'POST':
            form = SnapshotForm(request.POST, instance=snap)
            if form.is_valid():
                form.save()
                messages.success(request, "Updated snapshot description")
                return redirect('snapshot_detail', snap_id)
        else:
            form = SnapshotForm(instance=snap)

    return {
        'snapshot': snap,
        'form': form,
    }


class SnapshotForm(ModelForm):
    class Meta:
        model = Snapshot
        fields = ['title', 'description']

    title = CharField()


def snapshot_file(request, snap_id, format):
    snap = get_object_or_404(Snapshot, pk=snap_id)
    f = first(where(snap.files, format=format))
    return redirect(f.url)


@login_required
@render_to('snapshots/list.j2')
@paginate('snapshots', 10)
def my_snapshots(request):
    return {'snapshots': Snapshot.objects.filter(author=request.user).order_by('-frozen_on')}


import re
import requests
import oauth2access
import djapi as api


@api.catch(requests.RequestException, status=502)
@oauth2access.require('zenodo')
def upload_to_zenodo(request, snap_id):
    snap = get_object_or_404(Snapshot, pk=snap_id)

    # Minimum length for title and description on zenodo is 3
    if len(snap.title) < 3:
        return api.json(400, detail='Need title of length 3 or more')
    description = snap.description if len(snap.description) >= 3 else 'no description'

    # Create deposition
    meta = {
        'title': snap.title,
        'description': description,
        'upload_type': 'dataset',
        'creators': [{'name': '%s, %s' % (request.user.last_name, request.user.first_name)}],
    }
    res = request.zenodo.post('https://zenodo.org/api/deposit/depositions', json={'metadata': meta})
    res.raise_for_status()
    snap.zenodo = deposit = res.json()
    snap.save()

    # Upload files
    for file in snap.files:
        name = re.sub(r'\W+', '-', snap.title).strip('-').lower() or 'file'
        filename = '%s.%s' % (name, file['format'])
        data = {'filename': filename}
        files = {'file': file.open()}
        res = request.zenodo.post(deposit['links']['files'], data=data, files=files)
        res.raise_for_status()

        # Rename file, see Zenodo bug https://github.com/zenodo/zenodo/issues/940
        file_desc = res.json()
        if file_desc['filename'] != filename:
            res = request.zenodo.put(file_desc['links']['self'], json={'filename': filename})
            res.raise_for_status()

    # Publish
    res = request.zenodo.post(deposit['links']['publish'])
    res.raise_for_status()

    # Update info
    res = request.zenodo.get(deposit['links']['self'])
    res.raise_for_status()
    snap.zenodo = deposit = res.json()
    snap.save()

    return api.json(deposit)


@oauth2access.authorize('zenodo')
def authorize_zenodo(request):
    if request.zenodo:
        messages.success(request,
                         "Successfully authorized on zenodo, you can now upload your snapshot")
    else:
        messages.error(request, "Failed to get Zenodo access")
    return redirect(request.GET.get('next') or my_snapshots)
