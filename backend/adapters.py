# adapters.py

from haystack.fields import CharField, IntegerField
from haystack.indexes import SearchIndex, Indexable
from oscar.apps.catalogue.models import Product

class ProductIndex(SearchIndex, Indexable):
    text = CharField(document=True, use_template=True)
    product_id = IntegerField(model_attr='id')
    title = CharField(model_attr='title')
    description = CharField(model_attr='description')

    def get_model(self):
        return Product

    def index_queryset(self, using=None):
        return self.get_model().objects.all()