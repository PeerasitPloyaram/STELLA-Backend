import mariadb
import sys, os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.services.user import creatHash


load_dotenv()
connection = mariadb.connect(
    user=os.getenv("DB_CLIENT_USER"),
    password=os.getenv("DB_CLIENT_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv('DB_DATABASE_NAME')
)

cursor = connection.cursor()

def initCorpusSchemaCollections():
    sql_industry = """
    CREATE TABLE IF NOT EXISTS industries (
        industry_id int NOT NULL AUTO_INCREMENT,
        industry_name varchar(256) NOT NULL UNIQUE,
        abbr varchar(32) NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (industry_id)
    );
    """
    cursor.execute(sql_industry)

    sql_sector = """
    CREATE TABLE IF NOT EXISTS sectors (
        sector_id int NOT NULL AUTO_INCREMENT,
        sector_name varchar(256) NOT NULL,
        abbr varchar(32) NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (sector_id),
        industry_id int NOT NULL,
        FOREIGN KEY (industry_id) REFERENCES industries(industry_id)
    );
    """
    cursor.execute(sql_sector)

    sql_location_storage = """
    CREATE TABLE IF NOT EXISTS location_storages (
        location_storage_id int NOT NULL AUTO_INCREMENT,
        collection_name varchar(64) NOT NULL,
        partition_name varchar(64) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (location_storage_id)
    );
    """
    cursor.execute(sql_location_storage)

    sql_document = """
    CREATE TABLE IF NOT EXISTS documents (
        document_id int NOT NULL AUTO_INCREMENT,
        document_name varchar(64) NOT NULL,
        description text NOT NULL,
        is_active BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (document_id),
        location_storage_id int NOT NULL,
        FOREIGN KEY (location_storage_id) REFERENCES location_storages(location_storage_id)
    );
    """
    cursor.execute(sql_document)
    

    sql_company = """
    CREATE TABLE IF NOT EXISTS companies (
        company_id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
        company_name_th varchar(256),
        company_name_en varchar(256),
        abbr varchar(16) NOT NULL,
        is_active BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        sector_id int NOT NULL,
        location_storage_id int NOT NULL,
        FOREIGN KEY (sector_id) REFERENCES sectors(sector_id),
        FOREIGN KEY (location_storage_id) REFERENCES location_storages(location_storage_id)
    );
    """
    cursor.execute(sql_company)

    sql_company_file = """
    CREATE TABLE IF NOT EXISTS company_files (
        file_id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
        file_name varchar(256),
        file_type varchar(16),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        company_id int NOT NULL,
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
    );
    """
    cursor.execute(sql_company_file)

    connection.commit()
    print("Create Schma Successfuly.")
 
def initUserSchemaCollection():
    role = """
    CREATE TABLE IF NOT EXISTS roles (
        role_id int NOT NULL AUTO_INCREMENT,

        name varchar(256) NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        PRIMARY KEY (role_id)
    );
    """
    cursor.execute(role)


    user = """
    CREATE TABLE IF NOT EXISTS users (
        user_id UUID NOT NULL,
        role_id int NOT NULL,

        username varchar(256) NOT NULL UNIQUE,
        password varbinary(256) NOT NULL,
        email varchar(256) NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        PRIMARY KEY (user_id),
        FOREIGN KEY (role_id) REFERENCES roles(role_id)
    );
    """
    cursor.execute(user)



    session = """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        chat_session_uuid UUID NOT NULL,
        user_id UUID NULL,

        user_type ENUM('guest', 'user') NOT NULL,
        share BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        expire_at TIMESTAMP ,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        PRIMARY KEY (chat_session_uuid),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """
    cursor.execute(session)


    message = """
    CREATE TABLE IF NOT EXISTS messages (
        message_id int NOT NULL AUTO_INCREMENT,
        chat_session_uuid UUID NOT NULL,

        message TEXT NOT NULL,
        role ENUM('system', 'human') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        PRIMARY KEY (message_id),
        FOREIGN KEY (chat_session_uuid) REFERENCES chat_sessions(chat_session_uuid) ON DELETE CASCADE
    );
    """
    cursor.execute(message)
    connection.commit()


def initRoleData():
    sql = """
    INSERT INTO roles (name)
    VALUES
    ('user'),
    ('admin');
    """
    cursor.execute(sql)
    connection.commit()

def initData():
    sql = """
    INSERT INTO industries (industry_name, abbr)
    VALUES
    ('Agro & Food Industry', '.AGRO'),
    ('Consumer Products', '.CONSUMP'),
    ('Financials', '.FINCIAL'),
    ('Industrials', '.INDUS'),
    ('Property & Construction', '.PROPCON'),
    ('Resources', '.RESOURC'),
    ('Services', '.SERVICE'),
    ('Technology', '.TECH')
    ;
    """
    cursor.execute(sql)

    sql = """
    INSERT INTO sectors (sector_name, abbr, industry_id)
    VALUES
    ('Agribusiness', 'AGRI', 1),
    ('Food & Beverage', 'FOOD', 1),

    ('Fashion', 'FASHION', 2),
    ('HOME & Office Products', 'HOME', 2),
    ('Personal Products & Pharmaceuticals', 'PERSON', 2),

    ('Banking', 'BANK', 3),
    ('Finance & Securities', 'FIN', 3),
    ('Insurance', 'INSUR', 3),

    ('Automotive', 'AUTO', 4),
    ('Industrial Materials & Machinery', 'IMM', 4),
    ('Paper & Printing Materials', 'PAPER', 4),
    ('Petrochemicals & Chemicals', 'PETRO', 4),
    ('Packaging', 'PKG', 4),
    ('Steel & Metal Products', 'STEEL', 4),

    ('Construction Materials', 'CONMAT', 5),
    ('Construction Services', 'CONS', 5),
    ('Property Fund & REITs', 'PF&REITs', 5),
    ('Property Development', 'PROP', 5),

    ('Energy & Utilities', 'ENERG', 6),
    ('Mining', 'MINE', 6),

    ('Commaerce', 'COMM', 7),
    ('Health Care Services', 'HELTH', 7),
    ('Media & Publishing', 'MEDIA', 7),
    ('Professional Services', 'PROF', 7),
    ('Tourism & Leisure', 'TOURISM', 7),
    ('Transportation & Logistics', 'TRANS', 7),

    ('Electronic Components', 'ETRON', 8),
    ('Information & Communication Technology', 'ICT', 8)
    ;
    """
    cursor.execute(sql)
    connection.commit()

def dropAllTables():
    sql = "DROP TABLES IF EXISTS company_files;"
    cursor.execute(sql)
    
    sql = "DROP TABLES IF EXISTS companies, documents, location_storages;"
    cursor.execute(sql)

    sql = "DROP TABLES IF EXISTS sectors;"
    cursor.execute(sql)

    sql = "DROP TABLES IF EXISTS industries;"
    cursor.execute(sql)
    connection.commit()


    sql = "DROP TABLES IF EXISTS messages, chat_sessions"
    cursor.execute(sql)
    connection.commit()

    sql = "DROP TABLES IF EXISTS users, roles"
    cursor.execute(sql)
    connection.commit()



def initAdminUser():
    import uuid
    admin_passw = os.getenv("STELLA_ADMIN_PASSWORD")
    hash = creatHash(admin_passw)
    uuid = str(uuid.uuid4())
    admin = f'INSERT INTO users (user_id, role_id, username, password, email) VALUES ("{uuid}", "2", "stella", "{hash.decode()}", "stella_admin@gmail.com");'
    cursor.execute(admin)
    connection.commit()

def createDeleteSessionSchuduled():
    sql = "SET GLOBAL event_scheduler = ON;"
    cursor.execute(sql)
    connection.commit()

    sql = f"""
    CREATE EVENT IF NOT EXISTS delete_expired_sessions
    ON SCHEDULE EVERY 10 MINUTE
    DO
    BEGIN
        DELETE FROM chat_sessions WHERE expire_at IS NOT NULL AND expire_at < NOW();
    END
    """
    cursor.execute(sql)
    connection.commit()

if __name__ == "__main__":
    dropAllTables()
    initCorpusSchemaCollections()
    initUserSchemaCollection()
    initRoleData()
    initData()
    initAdminUser()
    createDeleteSessionSchuduled()