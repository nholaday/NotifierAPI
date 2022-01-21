from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from notifier import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('', views.api_root),
    path('preference/', views.UserPrefDetail.as_view(), name='preference'),
    path('notify/', views.SendNotification.as_view(), name='notify'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# allows to append .json or .api to request to specify Accept type
urlpatterns = format_suffix_patterns(urlpatterns)

# add a login link in the top right of every page
urlpatterns += [
    path('api-auth/', include('rest_framework.urls')),
]
