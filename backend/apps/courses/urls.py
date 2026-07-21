from django.urls import path
from .views import (
    CourseListView, CourseDetailView, EnrollView, MyEnrollmentsView, BulkEnrollView,
    WatchlistToggleView, InstructorCoursesView, CourseStudentsView,
    MaterialListView, AdminMaterialListView, AdminMaterialDetailView, MyLessonsView,
)

urlpatterns = [
    path('',                       CourseListView.as_view(),    name='course_list'),
    # NOTE: every literal single-segment path (my-enrollments/, my-lessons/, etc.) must be
    # listed BEFORE the <slug:slug>/ catch-all below — Django resolves top-to-bottom and
    # the slug converter greedily matches any of these names too, silently 404ing them
    # (pre-existing bug: this previously made /my-enrollments/ unreachable — fixed here).
    path('<int:course_id>/enroll/', EnrollView.as_view(),        name='enroll'),
    path('my-enrollments/',        MyEnrollmentsView.as_view(), name='my_enrollments'),
    path('my-lessons/',             MyLessonsView.as_view(),     name='my_lessons'),
    path('bulk-enroll/',           BulkEnrollView.as_view(),    name='bulk_enroll'),
    path('watchlist/',                          WatchlistToggleView.as_view(),  name='watchlist_list'),
    path('watchlist/<int:lesson_id>/',          WatchlistToggleView.as_view(),  name='watchlist_toggle'),
    path('instructor/',                         InstructorCoursesView.as_view(), name='instructor_courses'),
    path('instructor/<int:course_id>/students/', CourseStudentsView.as_view(),   name='course_students'),
    path('materials/',                          MaterialListView.as_view(),       name='material_list'),
    path('admin/materials/',                    AdminMaterialListView.as_view(),  name='admin_material_list'),
    path('admin/materials/<int:pk>/',           AdminMaterialDetailView.as_view(), name='admin_material_detail'),
    path('<slug:slug>/',            CourseDetailView.as_view(),  name='course_detail'),
]
