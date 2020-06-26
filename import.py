import os
import csv
from sqlalchemy.sql import text
from sqlalchemy import create_engine, Table, Column, Integer, String, Sequence, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine(os.getenv("DATABASE_URL"))
conn = engine.connect()

metadata = MetaData()

# create the books table
books = Table("books", metadata,
Column("isbn", String),
Column("title", String),
Column("author", String),
Column("year", Integer))

# create the users table
users = Table('users', metadata,
Column('id', Integer, Sequence('users_id_seq')),
Column('username', String, primary_key = True),
Column('hash', String))

# create the comments table
reviews = Table("reviews", metadata,
Column ("book_isbn", String),
Column("user_id", String),
Column("review", String),
Column("rating", Integer))

db = scoped_session(sessionmaker(bind=engine))

s = text("INSERT INTO books(isbn, title, author, year) VALUES(:a, :b, :c, :d)")

with open("books.csv") as csv_file:
	csv_reader = csv.reader(csv_file, delimiter = ",")
	line_count = 0

	for row in csv_reader:

		# skip the headers
		if line_count == 0:
			line_count += 1

		else:
			conn.execute(s, a = row[0], b = row[1], c = row[2], d = row[3])
			line_count += 1