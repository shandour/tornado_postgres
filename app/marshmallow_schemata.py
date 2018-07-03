from marshmallow import (
    Schema,
    fields,
    validate,
    validates,
    decorators,
    ValidationError)
from sqlalchemy import create_engine

from .db import bloggers
from local_settings import local_settings_dict


class MySchema(Schema):
    class Meta:
        exclude = ('_xsrf',)


class PostSchema(MySchema):
    topic = fields.String(validate=validate.Length(max=100))
    content = fields.String(required=True, validate=validate.Length(min=1))


class LoginSchema(MySchema):
    password = fields.String(required=True,
                             validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True,
                         validate=validate.Length(min=1, max=100))


class RegisterSchema(LoginSchema):
    username = fields.String(required=True,
                             validate=validate.Length(min=1, max=100))
    confirm_password = fields.String(required=True,
                                     validate=validate.Length(min=1, max=100))

    @decorators.validates_schema
    def validate_password(self, data):
        if not data.get('password') or not data.get('confirm_password'):
            return
        if data['password'] != data['confirm_password']:
            raise ValidationError('The passwords do not match',
                                  field_names=['password', 'confirm_password'])

    @validates('username')
    def validate_username(self, value):
        engine = create_engine(local_settings_dict['database'])
        with engine.connect() as conn:
            r = conn.execute(bloggers.select(bloggers.c.username == value))\
                    .fetchone()
            if r:
                raise ValidationError('Username already taken')
            else:
                return value

    @validates('email')
    def validate_email(self, value):
        engine = create_engine(local_settings_dict['database'])
        with engine.connect() as conn:
            r = conn.execute(bloggers.select(bloggers.c.email == value))\
                    .fetchone()
            if r:
                raise ValidationError('Email already taken')
            else:
                return value


class MessageSchema(LoginSchema):
    addressee = fields.String(required=True,
                              validate=validate.Length(min=1, max=100))
    content = fields.String(required=True,
                            validate=validate.Length(min=1))
    topic = fields.String(validate=validate.Length(min=1, max=100))

    @validates('addressee')
    def validate_addressee(self, value):
        bloggers_clmn = (bloggers.c.email if '@' and '.' in value
                         else bloggers.c.username)

        engine = create_engine(local_settings_dict['database'])
        with engine.connect() as conn:
            r = conn.execute(bloggers.select(bloggers_clmn == value))\
                    .fetchone()
            if not r:
                raise ValidationError('Incorrect username or email.')
            else:
                return value


class SearchSchema(MySchema):
    option = fields.List(fields.String(),
                         required=True,
                         validate=validate.ContainsOnly(['bloggers',
                                                         'topics']))
    query = fields.String(required=True,
                          validate=validate.Length(min=1, max=100))
