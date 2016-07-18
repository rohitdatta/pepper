"""empty message

Revision ID: 29033582c021
Revises: None
Create Date: 2016-07-13 23:27:23.301112

"""

# revision identifiers, used by Alembic.
revision = '29033582c021'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=128), nullable=True),
    sa.Column('fname', sa.String(length=128), nullable=True),
    sa.Column('lname', sa.String(length=128), nullable=True),
    sa.Column('status', sa.String(length=255), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('class_standing', sa.String(length=255), nullable=True),
    sa.Column('major', sa.String(length=255), nullable=True),
    sa.Column('shirt_size', sa.String(length=255), nullable=True),
    sa.Column('dietary_restrictions', sa.String(length=255), nullable=True),
    sa.Column('birthday', sa.Date(), nullable=True),
    sa.Column('gender', sa.String(length=255), nullable=True),
    sa.Column('phone_number', sa.String(length=255), nullable=True),
    sa.Column('school', sa.String(length=255), nullable=True),
    sa.Column('special_needs', sa.Text(), nullable=True),
    sa.Column('checked_in', sa.Boolean(), nullable=True),
    sa.Column('access_token', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('users')
    ### end Alembic commands ###