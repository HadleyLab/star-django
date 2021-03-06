from funcy import ldistinct, keep, re_all, lwithout

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_pandas.managers import DataFrameManager
from handy.models import JSONField


SPECIES = {'9606': 'human', '10090': 'mouse', '10116': 'rat'}


class Platform(models.Model):
    gpl_name = models.TextField()
    specie = models.CharField(max_length=127, blank=False, default='human')
    probes_total = models.IntegerField(null=True)
    probes_matched = models.IntegerField(null=True)
    verdict = models.CharField(max_length=127, blank=True)
    last_filled = models.DateTimeField(blank=True, null=True)
    stats = JSONField(default={})
    history = JSONField(default=[])

    class Meta:
        db_table = 'platform'

    def __str__(self):
        return self.gpl_name


class PlatformProbe(models.Model):
    # The next line is phony primary_key to stop Django from creating id field.
    # Field plus index weighed almost 2GB as of June 2017, so I got rid of them.
    platform = models.ForeignKey(Platform, related_name='probes', primary_key=True)
    probe = models.TextField()
    mygene_sym = models.TextField()
    mygene_entrez = models.IntegerField()

    objects = DataFrameManager()

    class Meta:
        db_table = 'platform_probe'


class Series(models.Model):
    gse_name = models.TextField()
    specie = models.CharField(max_length=127, blank=True)
    attrs = JSONField(default={}, blank=True)
    platforms = ArrayField(models.CharField(max_length=127), default=[], blank=True)
    samples_count = models.IntegerField(default=0, blank=True)

    class Meta:
        verbose_name_plural = 'series'
        db_table = 'series'

    def __str__(self):
        return self.gse_name

    def save(self, **kwargs):
        # Only set specie when it's non-controversial
        taxid = ldistinct(keep(self.attrs.get, ['platform_taxid', 'sample_taxid']))
        if len(taxid) == 1:
            self.specie = SPECIES.get(taxid[0])
        else:
            self.specie = ''

        self.platforms = re_all(r'GPL\d+', self.attrs['platform_id'])
        self.samples_count = len(self.attrs['sample_id'].split())

        super(Series, self).save(**kwargs)


class Sample(models.Model):
    series = models.ForeignKey('Series', related_name='samples', db_index=True)
    platform = models.ForeignKey(Platform, db_index=False)
    gsm_name = models.TextField()
    attrs = JSONField(default={})
    # TODO: refactor deleted -> is_active, get rid of char boolean
    # NOTE: leaving it as is for now to not mess with sample_view
    # is_active = models.BooleanField(default=True)
    deleted = models.CharField(max_length=1, blank=True, null=True)
    # This field store 'T' for deleted itmes.
    # Active items have 'F' or None

    class Meta:
        db_table = 'sample'


from s3field import S3Field

def analysis_s3name(self):
    return '%s-%s' % (self.pk, self.analysis_name)

class Analysis(models.Model):
    analysis_name = models.CharField(max_length=512)
    description = models.CharField(max_length=512, blank=True, default='')
    specie = models.CharField(max_length=127, blank=True,
                              choices=[('human', 'human'), ('mouse', 'mouse'), ('rat', 'rat')])
    case_query = models.CharField(max_length=512)
    control_query = models.CharField(max_length=512)
    modifier_query = models.CharField(max_length=512, blank=True, default='')
    min_samples = models.IntegerField(blank=True, null=True, default=3)
    # Reproducibility
    df = S3Field(null=True, make_name=analysis_s3name)
    fold_changes = S3Field(null=True, make_name=analysis_s3name, compress=True)
    # Stats
    series_count = models.IntegerField(blank=True, null=True)
    platform_count = models.IntegerField(blank=True, null=True)
    sample_count = models.IntegerField(blank=True, null=True)
    # TODO: make these JSON or ArrayFields?
    series_ids = models.TextField(blank=True)
    platform_ids = models.TextField(blank=True)
    sample_ids = models.TextField(blank=True)
    # Meta
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    created_by = models.ForeignKey('core.User', db_column='created_by', blank=True, null=True)
    modified_on = models.DateTimeField(blank=True, null=True, auto_now=True)
    modified_by = models.ForeignKey('core.User', db_column='modified_by', blank=True, null=True,
                                    related_name='+')
    success = models.BooleanField(default=False)

    class Meta:
        db_table = 'analysis'

    def __str__(self):
        if self.modifier_query:
            return '%s: case=%s control=%s modifier=%s' \
                % (self.analysis_name, self.case_query, self.control_query, self.modifier_query)
        else:
            return '%s: case=%s control=%s' \
                % (self.analysis_name, self.case_query, self.control_query)

    def results_df(self):
        qs = MetaAnalysis.objects.filter(analysis=self)
        fieldnames = lwithout([f.name for f in MetaAnalysis._meta.fields], 'id', 'analysis')
        return qs.to_dataframe(fieldnames, index='mygene_sym')


class MetaAnalysis(models.Model):
    analysis = models.ForeignKey(Analysis, db_index=True)
    mygene_sym = models.CharField("sym", max_length=512)
    mygene_entrez = models.IntegerField("entrez")
    direction = models.CharField(max_length=512)
    k = models.IntegerField()
    casedatacount = models.IntegerField('cases')
    controldatacount = models.IntegerField('controls')
    random_pval = models.FloatField(blank=True, null=True)
    random_te = models.FloatField(blank=True, null=True)
    random_se = models.FloatField(blank=True, null=True)
    random_lower = models.FloatField(blank=True, null=True)
    random_upper = models.FloatField(blank=True, null=True)
    random_zscore = models.FloatField(blank=True, null=True)
    fixed_pval = models.FloatField(blank=True, null=True)
    fixed_te = models.FloatField(blank=True, null=True)
    fixed_se = models.FloatField(blank=True, null=True)
    fixed_lower = models.FloatField(blank=True, null=True)
    fixed_upper = models.FloatField(blank=True, null=True)
    fixed_zscore = models.FloatField(blank=True, null=True)
    predict_te = models.FloatField(blank=True, null=True)
    predict_se = models.FloatField(blank=True, null=True)
    predict_lower = models.FloatField(blank=True, null=True)
    predict_upper = models.FloatField(blank=True, null=True)
    predict_pval = models.FloatField(blank=True, null=True)
    predict_zscore = models.FloatField(blank=True, null=True)
    tau2 = models.FloatField(blank=True, null=True)
    tau2_se = models.FloatField(blank=True, null=True)
    c = models.FloatField(blank=True, null=True)
    h = models.FloatField(blank=True, null=True)
    h_lower = models.FloatField(blank=True, null=True)
    h_upper = models.FloatField(blank=True, null=True)
    i2 = models.FloatField(blank=True, null=True)
    i2_lower = models.FloatField(blank=True, null=True)
    i2_upper = models.FloatField(blank=True, null=True)
    q = models.FloatField(blank=True, null=True)
    q_df = models.FloatField(blank=True, null=True)

    objects = DataFrameManager()

    class Meta:
        db_table = 'meta_analysis'
