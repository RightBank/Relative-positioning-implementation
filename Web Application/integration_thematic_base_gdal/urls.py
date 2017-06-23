from django.conf.urls import url

from . import views

app_name = 'integration_thematic_base_gdal'
urlpatterns = [

    url(r'^$', views.web_map, name='web_map'),

]