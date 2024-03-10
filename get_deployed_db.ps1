# Replace the local DB with the deployed one from Heroku
# https://devcenter.heroku.com/articles/heroku-postgres-import-export

heroku pg:backups:capture
heroku pg:backups:download
pg_restore --verbose --clean --no-acl --no-owner -h localhost -U david -d financial-monitor latest.dump

# rm latest.dump