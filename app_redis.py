# /usr/bin/python2.7
import psycopg2
import redis
from configparser import ConfigParser
from flask import Flask, request, render_template, g, abort
import time


def config(section, filename='config/database.ini'):

    parser = ConfigParser()
    parser.read(filename)

    db = {}
    if parser.has_section(section):
        for i in parser.items(section):
            db[i[0]] = i[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


def conn_postgres():
    try:
        db = config('postgresql')
        print('Connecting to PostgreSQL database...')
        return psycopg2.connect(**db)

    except(Exception, psycopg2.DatabaseError) as error:
        print('Connection to PostgreSQL error:', error)
        raise error


def conn_redis():
    try:
        db = config('redis')
        print('Connecting to Redis...')
        return redis.Redis.from_url(**db)

    except Exception as error:
        print('Connetion to Redis error', error)
        raise error


def fetch():

    query_str = 'select slow_version();'
    redis_key = 'slow_version'
    redis_ttl = 10


    connect_to_redis = conn_redis()

    try:
        value = connect_to_redis.get(redis_key)
        if value is not None:
            return value.decode('utf-8')

    except Exception as error:
        print('fetch error:', error)
        raise error

    finally:
        connect_to_redis.close()
        print('fetch redis connection closed')

    connect_to_postgres = conn_postgres()
    cursor = connect_to_postgres.cursor()

    try:
        cursor.execute(query_str)
        value = cursor.fetchone()[0]
        
        connect_to_redis.set(redis_key, value.encode('utf-8'), ex=redis_ttl)
        return value

    except Exception as error:
        print('fetch error:', error)
        raise error

    finally:
        cursor.close()
        connect_to_postgres.close()
        print('fetch postgres connection closed')

app = Flask(__name__)


@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.request_time = lambda: "%.5fs" % (time.time() - g.request_start_time)


@app.route("/")
def index():
    sql = 'SELECT slow_version();'
    db_result = fetch(sql)

    if(db_result):
        db_version = ''.join(db_result)
    else:
        abort(500)
    params = config()
    return render_template('index.html', db_version= db_version, db_host = params['host'])


if __name__ == "__main__":
    app.run()
