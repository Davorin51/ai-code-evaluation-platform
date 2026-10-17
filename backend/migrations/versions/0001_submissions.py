"""Persist reproducible evaluations."""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('submissions', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('challenge_id', sa.String(80), nullable=False), sa.Column('label', sa.String(100), nullable=False),
        sa.Column('origin', sa.String(30), nullable=False), sa.Column('code', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('result', sa.JSON(), nullable=False))
    op.create_index('ix_submissions_challenge_id', 'submissions', ['challenge_id'])

def downgrade():
    op.drop_index('ix_submissions_challenge_id', table_name='submissions')
    op.drop_table('submissions')
