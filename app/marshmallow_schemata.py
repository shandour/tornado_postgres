from marshmallow import (
    Schema,
    fields,
    validate,
    decorators,
    ValidationError)


class PostSchema(Schema):
    topic = fields.String(validate=validate.Length(max=100))
    content = fields.String(required=True)


class BloggerSchema(Schema):
    username = fields.String(required=True,
                             validate=validate.Length(max=200))
    email = fields.Email(required=True,
                         validate=validate.Length(max=100))


class RegisterSchema(BloggerSchema):
    password = fields.String(required=True,
                             validate=validate.Length(max=100))
    confirm_password = fields.String(required=True,
                             validate=validate.Length(max=100))
    @decorators.validates_schema
    def validate_password(self, data):
        if data['password'] != data['confirm_password']:
            raise ValidationError('The passwords do not match', field_names=['password', 'confirm_password'])
