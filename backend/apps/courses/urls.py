from django.urls import path
from .views import (
    CourseListView, CourseDetailView, EnrollView, MyEnrollmentsView, BulkEnrollView,
    WatchlistToggleView, InstructorCoursesView, CourseStudentsView, InstructorListView,
    MaterialListView, AdminMaterialListView, AdminMaterialDetailView, MyLessonsView,
    AdminCourseListView, AdminCourseDetailView, AdminTopicListView, AdminTopicDetailView,
    AdminLessonListView, AdminLessonDetailView, AdminAssignmentListView, AdminAssignmentDetailView,
    AssignmentSubmitView, CategoryListView,
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
    path('instructors/',                        InstructorListView.as_view(),   name='instructor_list'),
    path('instructor/<int:course_id>/students/', CourseStudentsView.as_view(),   name='course_students'),
    path('materials/',                          MaterialListView.as_view(),       name='material_list'),
    path('admin/materials/',                    AdminMaterialListView.as_view(),  name='admin_material_list'),
    path('admin/materials/<int:pk>/',           AdminMaterialDetailView.as_view(), name='admin_material_detail'),
    path('admin/courses/',                              AdminCourseListView.as_view(),   name='admin_course_list'),
    path('admin/courses/<int:pk>/',                     AdminCourseDetailView.as_view(), name='admin_course_detail'),
    path('admin/courses/<int:course_id>/topics/',       AdminTopicListView.as_view(),    name='admin_topic_list'),
    path('admin/topics/<int:pk>/',                      AdminTopicDetailView.as_view(),  name='admin_topic_detail'),
    path('admin/topics/<int:topic_id>/lessons/',        AdminLessonListView.as_view(),   name='admin_lesson_list'),
    path('admin/lessons/<int:pk>/',                     AdminLessonDetailView.as_view(), name='admin_lesson_detail'),
    path('admin/topics/<int:topic_id>/assignments/',    AdminAssignmentListView.as_view(),   name='admin_assignment_list'),
    path('admin/assignments/<int:pk>/',                 AdminAssignmentDetailView.as_view(), name='admin_assignment_detail'),
    path('assignments/<int:pk>/submit/',                AssignmentSubmitView.as_view(),      name='assignment_submit'),
    path('categories/',                                 CategoryListView.as_view(),          name='category_list'),
    path('<slug:slug>/',            CourseDetailView.as_view(),  name='course_detail'),
]
