#  -*- coding: utf-8 -*-

import os

import click
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFError

from myblog.blueprints.admin import admin_bp
from myblog.blueprints.auth import auth_bp
from myblog.blueprints.blog import blog_bp
from myblog.extensions import bootstrap, db, ckeditor, moment,login_manager,csrf, migrate
from myblog.models import Admin, Post, Category, Comment,Link
from myblog.settings import config

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask('myblog')
    app.config.from_object(config[config_name])

    register_logging(app)
    register_extensions(app)
    register_blueprints(app)
    register_commands(app)
    register_errors(app)
    register_shell_context(app)
    register_template_context(app)
    register_template_filter(app)
    
    return app


def register_logging(app):
    # todo　通过邮件发送关键日志
    """
    注册日志功能
    :param app:
    :return:
    """
    # 日志记录器
    app.logger.setLevel(logging.INFO)  # 日志记录器等级

    formatter=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 日志处理器
    file_handler=RotatingFileHandler('logs/blog.log',maxBytes=10*1024*1024,backupCount=10)

    file_handler.setFormatter(formatter)  # 日志处理器输出的日志格式
    file_handler.setLevel(logging.INFO)  # 日志处理器接收的日志等级

    if not app.debug:  # 不是调试模式，启动日志记录器
        app.logger.addHandler(file_handler)


def register_extensions(app):
    """
    注册第三方扩展
    :param app:
    :return:
    """
    bootstrap.init_app(app)
    db.init_app(app)
    ckeditor.init_app(app)
    moment.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app,db)


def register_blueprints(app):
    """
    注册蓝图
    :param app:
    :return:
    """
    app.register_blueprint(blog_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp, url_prefix='/auth')


def register_template_filter(app):
    """
    注册模板过滤器
    :param app:
    :return:
    """
    @app.template_filter('post_comments_length')
    def post_comments_length(comments):
        """
        首页文章评论数过滤器
        :param comments: 
        :return: 
        """
        count=0
        for comment in comments:
            if comment.reviewed:
                count +=1
        return count


def register_shell_context(app):
    """
    向flask shell中添加变量
    :param app:
    :return:
    """
    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db, Admin=Admin, Post=Post, Category=Category, Comment=Comment)


def register_template_context(app):
    """
    添加模板上下文变量，方便在多个模板中共同使用
    :param app:
    :return:
    """
    @app.context_processor
    def make_template_context():
        admin = Admin.query.first()
        categories = Category.query.order_by(Category.name).all()
        links = Link.query.order_by(Link.name).all()
        # 未审核评论数
        unread_comments = None
        if current_user.is_authenticated:
            unread_comments = Comment.query.filter_by(reviewed=False).count()

        return dict(
            admin=admin, categories=categories,
            links=links, unread_comments=unread_comments)


def register_errors(app):
    """
    注册异常页面
    :param app:
    :return:
    """
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/400.html', description=e.description), 400


def register_commands(app):
    """
    自定义flask命令
    :param app:
    :return:
    """
    @app.cli.command()
    @click.option('--drop', is_flag=True, help='Create after drop.')
    def initdb(drop):
        """
        初始化数据库
        :param drop:
        :return:
        """
        if drop:
            click.confirm('This operation will delete the database, do you want to continue?', abort=True)
            db.drop_all()
            click.echo('Drop tables.')
        db.create_all()
        click.echo('Initialized database.')

    @app.cli.command()
    @click.option('--username', prompt=True, help='The username used to login.')
    @click.option('--password', prompt=True, hide_input=True,
                  confirmation_prompt=True, help='The password used to login.')
    def init(username, password):
        """
        注册管理员
        :param username:
        :param password:
        :return:
        """

        click.echo('Initializing the database...')
        db.create_all()

        admin = Admin.query.first()
        if admin is not None:
            click.echo('The administrator already exists, updating...')
            admin.username = username
            admin.set_password(password)
        else:
            click.echo('Creating the temporary administrator account...')
            admin = Admin(
                username=username,
                blog_title='Bluelog',
                blog_sub_title="No, I'm the real thing.",
                name='Admin',
                about='Anything about you.'
            )
            admin.set_password(password)
            db.session.add(admin)

        category = Category.query.first()
        if category is None:
            click.echo('Creating the default category...')
            category = Category(name='Default')
            db.session.add(category)

        db.session.commit()
        click.echo('Done.')

    @app.cli.command()
    @click.option('--category', default=10, help='Quantity of categories, default is 10.')
    @click.option('--post', default=50, help='Quantity of posts, default is 50.')
    @click.option('--comment', default=500, help='Quantity of comments, default is 500.')
    def forge(category, post, comment):
        """
        生成虚拟数据
        :param category:
        :param post:
        :param comment:
        :return:
        """
        from myblog.fakes import fake_admin, fake_categories, fake_posts, fake_comments, fake_links

        db.drop_all()
        db.create_all()

        click.echo('Generating the administrator...')
        fake_admin()

        click.echo('Generating %d categories...' % category)
        fake_categories(category)

        click.echo('Generating %d posts...' % post)
        fake_posts(post)

        click.echo('Generating %d comments...' % comment)
        fake_comments(comment)

        click.echo('Generating links...')
        fake_links()

        click.echo('Done.')

