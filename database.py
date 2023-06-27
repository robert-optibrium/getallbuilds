# coding=utf-8
# ref: https://towardsdatascience.com/how-to-connect-to-a-postgresql-database-with-python-using-ssh-tunnelling-d803282f71e7
# ref: https://www.pythoncentral.io/introductory-tutorial-python-sqlalchemy/
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import json
from utils import Utils
import pprint

utils = Utils()
Base = declarative_base()


class ShortAllBuilds(Base):
    __tablename__ = 'short_all_builds'
    id = Column(Integer, primary_key=True)
    displayname = Column(String(250), nullable=False)
    timestamp = Column(String(50), nullable=False)
    duration = Column(Integer, nullable=True)
    executor = Column(String(100), nullable=True)
    url = Column(String(250), nullable=True)

class Queue(Base):
    __tablename__ = 'queue'
    id = Column(Integer, primary_key=True)
    timestamp = Column(String(50), nullable=False)
    queue = Column(String(1024), nullable=False)

class QueueItem(Base):
    __tablename__ = 'queueitem'
    id = Column(Integer, primary_key=True)
    qid = Column(Integer)
    name = Column(String(250), nullable=True)
    url = Column(String(250), nullable=True)
    why = Column(String(150), nullable=True)

# noinspection PyPep8Naming
class Database:
    def __init__(self, initialize=False, dbconnection='localhost'):
        self.Qry_plain = "SELECT * FROM short_all_builds"
        self.Qry_builds = "SELECT timestamp from short_all_builds where displayname='{dn}' and timestamp='{ts}' and duration={du}"
        self.Qry_builds_Delete = \
            "DELETE from short_all_builds where displayname='{dn}' and timestamp='{ts}' and duration='{du}'"
        try:
            utils.logprint("Using DB Host index: {i}".format(i=dbconnection))
            self.creds = json.load(open("creds.config", 'r'))
            self.creds = [x for x in self.creds if x['name'] == dbconnection]
            self.creds = self.creds[0]   #list comprenhension ends up with a list element
        except Exception as e:
            print("Exception loading creds.config file: {e}".format(e=e))
            raise e
        self.engine = self.connect_sshengine(self.creds)
        # Create all tables in the engine. This is equivalent to "Create Table"
        # statements in raw SQL.
        Base.metadata.create_all(self.engine)
        DBSession = sessionmaker(bind=self.engine)
        self.session = DBSession()
        if initialize:
            # empty the tables in the database
            utils.logprint("Deleting table data")
            self.exec_qry_no_result("delete from short_all_builds")

    # noinspection PyBroadException
    @staticmethod
    def connect_sshengine(creds):
        try:

            utils.logprint('Connecting to Database on {h}'.format(h=creds["DB_HOST"]))
            constr = 'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(
                host=creds["DB_HOST"],
                port=creds["PORT"],
                user=creds["PG_DB_UN"],
                password=creds["PG_DB_PW"],
                db=creds["PG_DB_NAME"]
            )
            return create_engine(constr)
        except Exception as e:
            # noinspection PyUnboundLocalVariable
            utils.logprint('Connection Has Failed... Is AWS instance down?\nconstr={c}\nException={e}'.format(c=constr,
                                                                                                              e=e))
            raise e

    def Exec_Insert_build(self, displayname, timestamp, duration, executor, url):
        rows = self.exec_qry(self.Qry_builds.format(dn=displayname, ts=timestamp, du=duration))
        if rows:
            self.exec_qry(self.Qry_builds_Delete.format(dn=displayname, ts=timestamp, du=duration))
        new_rs = ShortAllBuilds(displayname=displayname, timestamp=timestamp, duration=duration, executor=executor,
                                url=url)
        self.session.add(new_rs)
        self.session.commit()
        self.session.flush()
        return new_rs.id

    def Exec_Insert_Queue(self, timestamp, queue):
        new_rs = Queue(timestamp=timestamp, queue=queue)
        self.session.add(new_rs)
        self.session.commit()
        self.session.flush()
        return new_rs.id

    def Exec_Insert_QueueItem(self, qid, name, url, why):
        new_rs = QueueItem(qid=qid, name=name, url=url, why=why)
        self.session.add(new_rs)
        self.session.commit()
        self.session.flush()
        return new_rs.id

    # noinspection PyBroadException,PyPep8,PyUnusedLocal
    def Exec_Qry_ShortBuilds(self):
        row = self.exec_qry(self.Qry_plain)
        try:
            return row[0][0]
        except Exception as e:
            return ''

    @staticmethod
    def cvtext(qry):
        return text(qry)

    def exec_qry(self, qry):
        result = []
        # print(qry)
        qry = self.cvtext(qry)
        try:
            with self.engine.connect() as con:
                rs = con.execute(qry)
                if rs.returns_rows:
                    for row in rs:
                        row = [str(x) for x in row]
                        result.append(row)
            return result
        except Exception as e:
            utils.logprint("Exception executing query {q}\nException: {e}".format(q=qry, e=e))

    def exec_qry_plain(self, qry):
        result = []
        qry = self.cvtext(qry)
        try:
            with self.engine.connect() as con:
                rs = con.execute(qry)
                for row in rs:
                    result.append(row)
            return result
        except Exception as e:
            utils.logprint("Exception executing query {q}\nException: {e}".format(q=qry, e=e))

    def exec_qry_no_result(self, qry):
        qry = self.cvtext(qry)
        try:
            with self.engine.connect() as con:
                con.execute(qry)
        except Exception as e:
            utils.logprint("Exception executing query {q}\nException: {e}".format(q=qry, e=e))
