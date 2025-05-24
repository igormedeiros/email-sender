import psycopg2
import psycopg2.extras # For dict cursors, good practice
import logging

logger = logging.getLogger(__name__)

def get_db_connection(config):
    """
    Establishes a connection to the PostgreSQL database using details from the config.

    Args:
        config: The application config object.

    Returns:
        A psycopg2 connection object or None if connection fails.
    """
    try:
        pg_config = config.postgres_config
        conn = psycopg2.connect(
            host=pg_config.get("host"),
            port=pg_config.get("port"),
            user=pg_config.get("user"),
            password=pg_config.get("password"),
            dbname=pg_config.get("db")
        )
        logger.info("Successfully connected to PostgreSQL database.")
        return conn
    except (psycopg2.Error, AttributeError, KeyError) as e:
        logger.error(f"Error connecting to PostgreSQL database: {e}")
        # If AttributeError or KeyError, it means pg_config or its keys are missing
        if isinstance(e, (AttributeError, KeyError)):
             logger.error("Check if postgres_config and its keys (host, port, user, password, db) are defined in the configuration.")
        return None

def create_unsubscribe_table(conn, table_name: str):
    """
    Creates the unsubscribe table if it doesn't already exist.

    Args:
        conn: Active psycopg2 connection object.
        table_name: Name of the unsubscribe table.
    """
    if not conn:
        logger.error("No database connection available for create_unsubscribe_table.")
        return

    # Using %s for table name is not safe due to SQL injection.
    # However, psycopg2 doesn't support identifiers in parameterized queries directly for CREATE TABLE.
    # Since table_name comes from config, it's considered a controlled source.
    # For dynamic table names from user input, use psycopg2.sql.Identifier
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        email TEXT PRIMARY KEY,
        unsubscribed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        with conn.cursor() as cur:
            cur.execute(create_table_query)
            conn.commit()
            logger.info(f"Table '{table_name}' created or already exists.")
    except psycopg2.Error as e:
        logger.error(f"Error creating table '{table_name}': {e}")
        conn.rollback() # Rollback in case of error

def add_email_to_unsubscribe_list(conn, email: str, table_name: str):
    """
    Adds an email to the unsubscribe list. Handles duplicates gracefully.

    Args:
        conn: Active psycopg2 connection object.
        email: The email address to add.
        table_name: Name of the unsubscribe table.
    """
    if not conn:
        logger.error("No database connection available for add_email_to_unsubscribe_list.")
        return

    # Using f-string for table_name is generally unsafe if table_name is from user input.
    # Here, table_name is from config, so it's a controlled value.
    # For user-provided table names, use psycopg2.sql.SQL and psycopg2.sql.Identifier.
    insert_query = f"""
    INSERT INTO {table_name} (email)
    VALUES (%s)
    ON CONFLICT (email) DO NOTHING;
    """
    try:
        with conn.cursor() as cur:
            cur.execute(insert_query, (email,))
            conn.commit()
            if cur.rowcount > 0:
                logger.info(f"Email '{email}' added to unsubscribe list in table '{table_name}'.")
            else:
                logger.info(f"Email '{email}' already in unsubscribe list or no action taken in table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error adding email '{email}' to table '{table_name}': {e}")
        conn.rollback()

def remove_email_from_unsubscribe_list(conn, email: str, table_name: str):
    """
    Removes an email from the unsubscribe list.

    Args:
        conn: Active psycopg2 connection object.
        email: The email address to remove.
        table_name: Name of the unsubscribe table.
    """
    if not conn:
        logger.error("No database connection available for remove_email_from_unsubscribe_list.")
        return

    delete_query = f"DELETE FROM {table_name} WHERE email = %s;"
    try:
        with conn.cursor() as cur:
            cur.execute(delete_query, (email,))
            conn.commit()
            if cur.rowcount > 0:
                logger.info(f"Email '{email}' removed from unsubscribe list in table '{table_name}'.")
            else:
                logger.warning(f"Email '{email}' not found in unsubscribe list table '{table_name}' or no action taken.")
    except psycopg2.Error as e:
        logger.error(f"Error removing email '{email}' from table '{table_name}': {e}")
        conn.rollback()

def get_unsubscribed_emails(conn, table_name: str) -> list[str]:
    """
    Fetches all emails from the unsubscribe table.

    Args:
        conn: Active psycopg2 connection object.
        table_name: Name of the unsubscribe table.

    Returns:
        A list of email strings, or an empty list if an error occurs or no emails are found.
    """
    if not conn:
        logger.error("No database connection available for get_unsubscribed_emails.")
        return []

    select_query = f"SELECT email FROM {table_name};"
    emails = []
    try:
        # Using psycopg2.extras.DictCursor to access columns by name, though not strictly needed for single column
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(select_query)
            rows = cur.fetchall()
            emails = [row['email'] for row in rows]
            logger.info(f"Retrieved {len(emails)} emails from unsubscribe list table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error fetching emails from table '{table_name}': {e}")
        # conn.rollback() is not strictly necessary for SELECT, but good practice if part of a larger transaction
    return emails

# Example Usage (Illustrative - requires a config object and running Postgres)
if __name__ == '__main__':
    # This is a placeholder for a proper Config object
    class MockConfig:
        @property
        def postgres_config(self):
            # Simulating config.postgres_config
            # Replace with your actual DB details for local testing
            return {
                "host": "localhost",
                "port": 5432,
                "user": "your_user", # Replace with your user
                "password": "your_password", # Replace with your password
                "db": "email_db_test", # Replace with your test DB
                "unsubscribe_table": "test_unsub_table" 
            }

    mock_config = MockConfig()
    unsubscribe_table_name = mock_config.postgres_config.get("unsubscribe_table")

    # Get connection
    connection = get_db_connection(mock_config)

    if connection:
        try:
            # Create table
            create_unsubscribe_table(connection, unsubscribe_table_name)

            # Add emails
            add_email_to_unsubscribe_list(connection, "test1@example.com", unsubscribe_table_name)
            add_email_to_unsubscribe_list(connection, "test2@example.com", unsubscribe_table_name)
            add_email_to_unsubscribe_list(connection, "test1@example.com", unsubscribe_table_name) # Duplicate

            # Get all unsubscribed emails
            unsubscribed = get_unsubscribed_emails(connection, unsubscribe_table_name)
            logger.info(f"Currently Unsubscribed: {unsubscribed}")

            # Remove an email
            remove_email_from_unsubscribe_list(connection, "test1@example.com", unsubscribe_table_name)
            
            # Get all unsubscribed emails again
            unsubscribed_after_removal = get_unsubscribed_emails(connection, unsubscribe_table_name)
            logger.info(f"Unsubscribed after removal: {unsubscribed_after_removal}")

            # Try to remove a non-existent email
            remove_email_from_unsubscribe_list(connection, "nonexistent@example.com", unsubscribe_table_name)

        finally:
            # Close the connection
            connection.close()
            logger.info("PostgreSQL connection closed.")
    else:
        logger.error("Failed to connect to the database. Example usage skipped.")

```
