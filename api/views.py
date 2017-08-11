from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render
import djapi as api

from s3field.ops import frame_dumps
from legacy.models import Series, Platform, PlatformProbe, Analysis
from tags.models import Tag


tags_qs = api.queryset(Tag).filter(is_active=True) \
    .values_but('created_by', 'modified_by', 'is_active', 'created_on', 'modified_on')

def tags(request):
    return api.json(tags_qs)

def tag_create(request):
    assert 0

# class TagForm(ModelForm):
#     class Meta:
#         model = Tag
#         fields = ['tag_name', 'description', 'ontology_id',
#                   'concept_full_id', 'concept_name']

#     def clean_tag_name(self):
#         tag_name = self.cleaned_data['tag_name']
#         if ' ' in tag_name:
#             raise ValidationError('Spaces are not allowed in tag names, use underscores instead.')
#         elif not re.search(r'^[a-zA-Z]\w+$', tag_name):
#             raise ValidationError('Wrong tag name format.')
#         return tag_name

#     def clean(self):
#         clean_data = super(TagForm, self).clean()
#         if 'tag_name' in clean_data and not self.instance.pk:
#             if Tag.objects.filter(tag_name=clean_data['tag_name'], is_active=True).exists():
#                 self.add_error('tag_name',
#                                'Tag with name "%s" already exists' % clean_data['tag_name'])

def tag_detail(request, pk):
    return api.json(api.get_or_404(tags_qs, pk=pk))


series_qs = api.queryset(Series).values_but('id', 'samples_count').order_by('id')

def series(request):
    return api.json(api.paginate(request, series_qs, per_page=10))

def series_detail(request, gse_name):
    return api.json(api.get_or_404(series_qs, gse_name=gse_name))

@api.catch(Series.DoesNotExist, status=404)
def series_samples(request, gse_name):
    series = Series.objects.get(gse_name=gse_name)
    # renames = {'series__gse_name': 'gse_name', 'platform__gpl_name': 'gpl_name'}
    samples = api.queryset(series.samples.exclude(deleted='T')).values(
        'gsm_name', 'attrs',
        series__gse_name='gse_name', platform__gpl_name='gpl_name')

    # Filter by platform
    if request.GET.get('gpl_name'):
        samples = samples.filter(platform__gpl_name=request.GET.get('gpl_name'))

    return api.json(samples)


platforms_qs = api.queryset(Platform).order_by('id') \
    .values_but('id', 'stats', 'history', 'verdict', 'last_filled')

def platforms(request):
    return api.json(api.paginate(request, platforms_qs, per_page=10))

def platform_detail(request, gpl_name):
    return api.json(api.get_or_404(platforms_qs, gpl_name=gpl_name))

def platform_probes(request, gpl_name):
    if not Platform.objects.filter(gpl_name=gpl_name).exists():
        return api.json_error(404, 'Platform not found')

    qs = PlatformProbe.objects.filter(platform__gpl_name=gpl_name)
    probes_df = qs.to_dataframe(
        fieldnames=['probe', 'mygene_sym', 'mygene_entrez']
    )
    return HttpResponse(frame_dumps(probes_df), content_type='application/json')


# Platforms = api.Resource(
#     Platform.objects.order_by('id'),
#     exclude=['id', 'stats', 'history', 'verdict', 'last_filled'],
# )
# platforms = Platforms.views.list()
# platforms_detail = Platforms.views.get(by='gpl_name')

# class Analysis(models.Model):
#     analysis_name = models.CharField(max_length=512)
#     description = models.CharField(max_length=512, blank=True, default='')
#     specie = models.CharField(max_length=127, blank=True,
#                               choices=[('human', 'human'), ('mouse', 'mouse'), ('rat', 'rat')])
#     case_query = models.CharField(max_length=512)
#     control_query = models.CharField(max_length=512)
#     modifier_query = models.CharField(max_length=512, blank=True, default='')
#     min_samples = models.IntegerField(blank=True, null=True, default=3)


from s3field.fields import Resource

analysis_qs = api.queryset(Analysis).filter(is_active=True) \
    .values_but('created_by', 'modified_by', 'is_active', 'created_on', 'modified_on',
                'series_ids', 'platform_ids', 'sample_ids') \
    .map_types(Resource, lambda r: r.url)

def analysis_list(request):
    return api.json(api.paginate(request, analysis_qs, per_page=10))

def analysis_detail(request, pk):
    return api.json(api.get_or_404(analysis_qs, pk=pk))


from analysis.views import AnalysisForm
from analysis.tasks import analysis_task

# TODO: a helper for this?
#       autouse when DEBUG=True?
#       integrate with get_post() to autoprovide url?
def analysis_form(request):
    form = AnalysisForm()
    return render(request, 'test_form.j2', {'form': form, 'action': reverse('analysis')})

@api.auth_required
@api.validate(form=AnalysisForm)
def analysis_create(request, analysis):
    analysis.created_by_id = analysis.modified_by_id = request.user.id
    analysis.save()
    analysis_task.delay(analysis.pk)
    return api.json({'created': analysis.pk})