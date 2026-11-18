from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # Home and general
    path('', views.home, name='home'),
    path('games/', views.game_list, name='game_list'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('game/<int:game_id>/like/', views.like_game, name='like_game'),
    
    # User authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User profile
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('ranking/', views.ranking, name='ranking'),
    
    # Threads and comments
    path('thread/<int:thread_id>/', views.thread_detail, name='thread_detail'),
    path('thread/<int:thread_id>/poll/', views.get_thread_updates, name='get_thread_updates'),
    path('thread/create/', views.create_thread, name='create_thread'), # Generic
    path('thread/create/<int:game_id>/', views.create_thread, name='create_thread_game'), # Specific
    path('thread/<int:thread_id>/edit/', views.edit_thread, name='edit_thread'),
    path('thread/<int:thread_id>/like/', views.like_thread, name='like_thread'),
    path('thread/<int:thread_id>/react/', views.react_thread, name='react_thread'),
    path('thread/<int:thread_id>/delete/', views.delete_thread, name='delete_thread'),
    
    # Comments
    path('comment/<int:thread_id>/add/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('comment/<int:comment_id>/react/', views.react_comment, name='react_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # Game guides
    path('guide/create/', views.create_guide, name='create_guide'), # Generic
    path('guide/<int:game_id>/create/', views.create_guide, name='create_guide_game'), # Specific
    path('guide/<int:guide_id>/', views.guide_detail, name='guide_detail'),
    path('guide/<int:guide_id>/poll/', views.get_guide_updates, name='get_guide_updates'),
    path('guide/<int:guide_id>/edit/', views.edit_guide, name='edit_guide'),
    path('guide/<int:guide_id>/like/', views.like_guide, name='like_guide'),
    path('guide/<int:guide_id>/react/', views.react_guide, name='react_guide'),
    path('guide/<int:guide_id>/delete/', views.delete_guide, name='delete_guide'),
    path('guides/<int:game_id>/', views.game_guides, name='game_guides'),
    
    # Guide comments
    path('guide/comment/<int:comment_id>/delete/', views.delete_guide_comment, name='delete_guide_comment'),
    path('guide/comment/<int:comment_id>/like/', views.like_guide_comment, name='like_guide_comment'),
    path('guide/comment/<int:comment_id>/react/', views.react_guide_comment, name='react_guide_comment'),
    
    # Groups
    path('groups/', views.group_chat_home, name='group_chat_home'),
    path('group/create/', views.create_group, name='create_group'),
    path('group/create/<int:game_id>/', views.create_group, name='create_group_game'),
    path('group/<int:group_id>/', views.group_detail, name='group_detail'),
    path('group/<int:group_id>/poll/', views.get_group_messages, name='get_group_messages'),
    path('group/<int:group_id>/join/', views.join_group, name='join_group'),
    path('group/<int:group_id>/leave/', views.leave_group, name='leave_group'),
    path('group/<int:group_id>/delete/', views.delete_group, name='delete_group'),
    path('group/<int:group_id>/message/<int:message_id>/delete/', views.delete_group_message, name='delete_group_message'),
    
    # Friends and messaging
    path('friends/', views.friends_list, name='friends_list'),
    path('add-friend/<str:username>/', views.add_friend, name='add_friend'),
    path('accept-friend/<int:friendship_id>/', views.accept_friend, name='accept_friend'),
    path('reject-friend/<int:friendship_id>/', views.reject_friend, name='reject_friend'),
    path('remove-friend/<str:username>/', views.remove_friend, name='remove_friend'),
    path('api/friend-status/<str:username>/', views.api_friend_status, name='api_friend_status'),
    
    # Direct messages
    path('messages/', views.inbox, name='inbox'),
    path('messages/<str:username>/', views.chat, name='chat'),
    path('message/send/', views.send_message, name='send_message'),
    path('messages/<str:username>/poll/', views.get_new_messages, name='get_new_messages'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('messages/<str:username>/delete/', views.delete_conversation, name='delete_conversation'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notification/<int:notification_id>/read/', views.read_notification, name='read_notification'),
    path('notification/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('api/unread-counts/', views.api_unread_counts, name='api_unread_counts'),
    
    # Reports
    path('report/create/', views.create_report, name='create_report'),
    path('report/thread/<int:thread_id>/', views.report_thread, name='report_thread'),
    path('report/guide/<int:guide_id>/', views.report_guide, name='report_guide'),
    path('report/comment/<int:comment_id>/', views.report_comment, name='report_comment'),
    path('report/user/<str:username>/', views.report_user, name='report_user'),
    
    # Search
    path('search/', views.search, name='search'),
    path('search/users/', views.search_users, name='search_users'),
    
    # Back-Office Staff Portal
    path('backoffice/', views.backoffice_dashboard, name='backoffice_dashboard'),
    path('backoffice/user/<int:user_id>/action/', views.backoffice_user_action, name='backoffice_user_action'),
    path('backoffice/report/<int:report_id>/action/', views.backoffice_report_action, name='backoffice_report_action'),
    path('backoffice/game/create/', views.backoffice_game_create, name='backoffice_game_create'),
    path('backoffice/game/<int:game_id>/edit/', views.backoffice_game_edit, name='backoffice_game_edit'),
    path('backoffice/game/<int:game_id>/delete/', views.backoffice_game_delete, name='backoffice_game_delete'),
    path('backoffice/thread/<int:thread_id>/delete/', views.backoffice_thread_delete, name='backoffice_thread_delete'),
    path('backoffice/comment/<int:comment_id>/delete/', views.backoffice_comment_delete, name='backoffice_comment_delete'),
    path('backoffice/guide/<int:guide_id>/delete/', views.backoffice_guide_delete, name='backoffice_guide_delete'),
    path('backoffice/group/<int:group_id>/delete/', views.backoffice_group_delete, name='backoffice_group_delete'),
]

