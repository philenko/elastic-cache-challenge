  
# /usr/bin/python2.7
import psycopg2
from configparser import ConfigParser
from flask import Flask, request, render_template, g, abort
import time
import redis

def config(section, filename='config/database.ini'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)
    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db

def get_postgres():
    params = config('postgresql')
    print('get_postgres() connecting to postgres...')
    return psycopg2.connect(**params)

def get_redis():
    params = config('redis')
    print('get_redis() connecting to redis...')
    return redis.Redis.from_url(**params)

def fetch(sql):
    query_str = 'select slow_version();'
    redis_key = 'slow_version'
    redis_ttl = 10

    redis_conn = get_redis()

    try:
        value = redis_conn.get(redis_key)
        if value is not None:
            return value.decode('utf-8')
    except Exception as error:
        print('select_version() error:', error)
        raise error
    finally:
        redis_conn.close()
        print('select_version() redis connection closed')

    postgres_conn = get_postgres()
    cursor = postgres_conn.cursor()
    try:
        # read value from database
        cursor.execute(query_str)
        value = cursor.fetchone()[0]

        # set value in cache
        redis_conn.set(redis_key, value.encode('utf-8'), ex=redis_ttl)
        return value

    except Exception as error:
        print('select_version() error:', error)
        raise error

    finally:
        cursor.close()
        postgres_conn.close()
        print('select_version() postgres connection closed')

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
    return render_template('index.html', db_version = db_version, db_host = params['host'])

if __name__ == "__main__":        # on running python app.py
    app.run()                     # run the flask app
