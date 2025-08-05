from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from wtforms.fields import FileField
from flask_wtf.file import FileAllowed, FileRequired

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6)
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')

class DocumentUploadForm(FlaskForm):
    file = FileField('Document', validators=[
        FileRequired(),
        FileAllowed(['txt', 'pdf', 'docx', 'json'], 'Only TXT, PDF, DOCX, and JSON files are allowed!')
    ])
    submit = SubmitField('Upload Document')

class QueryForm(FlaskForm):
    query = TextAreaField('Your Question', validators=[
        DataRequired(),
        Length(min=5, max=1000)
    ], render_kw={'rows': 3, 'placeholder': 'Ask a question about your documents...'})
    submit = SubmitField('Ask Question')