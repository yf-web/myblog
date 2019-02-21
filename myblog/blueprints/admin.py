from flask import Blueprint

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
def index():
    return 'admin page'


@admin_bp.route('/new_post')
def new_post():
    return 'new_post page'
