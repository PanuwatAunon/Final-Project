from .helpers import get_user_friend_ids, pending_reports_badge
from .auth import register, login_view, logout_view
from .home import home, game_list, game_detail, like_game
from .profile import user_profile, edit_profile, ranking
from .thread import thread_detail, create_thread, edit_thread, like_thread, delete_thread, react_thread, get_thread_updates
from .comment import add_comment, like_comment, delete_comment, react_comment
from .guide import (
    create_guide, guide_detail, edit_guide, like_guide, delete_guide,
    game_guides, delete_guide_comment, like_guide_comment, react_guide, react_guide_comment, get_guide_updates
)
from .group import (
    group_chat_home, create_group, group_detail, delete_group_message,
    join_group, leave_group, delete_group, get_group_messages
)
from .friend import friends_list, add_friend, accept_friend, reject_friend, remove_friend, api_friend_status
from .message import get_new_messages, inbox, chat, send_message, delete_message, delete_conversation
from .notification import notifications, read_notification, delete_notification, clear_notifications, api_unread_counts
from .report import create_report, report_thread, report_guide, report_comment, report_user
from .search import search, search_users
from .backoffice import (
    backoffice_dashboard, backoffice_user_action, backoffice_report_action,
    backoffice_game_create, backoffice_game_edit, backoffice_game_delete,
    backoffice_thread_delete, backoffice_comment_delete, backoffice_guide_delete,
    backoffice_group_delete
)

