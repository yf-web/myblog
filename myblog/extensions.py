from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

bootstrap = Bootstrap()
db = SQLAlchemy()
ckeditor = CKEditor()
moment = Moment()
csrf=CSRFProtect()
login_manager=LoginManager()
migrate=Migrate()

# 视图保护
login_manager.login_view='auth.login'
login_manager.login_message_category='warning'
login_manager.login_message=u"请先登录！"


@login_manager.user_loader
def load_user(user_id):
    from myblog.models import Admin
    user=Admin.query.get(int(user_id))
    return user