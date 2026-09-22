import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Try importing pyTigerGraph
try:
    import pyTigerGraph as tg
    HAS_PYTIGERGRAPH = True
except ImportError:
    HAS_PYTIGERGRAPH = False
    logger.warning("pyTigerGraph library not found. Will use mock schema manager fallback.")

SCHEMA_GSQL = """
CREATE VERTEX User (PRIMARY_ID id STRING, name STRING, email STRING, phone STRING, created_at STRING, risk_score DOUBLE, status STRING) WITH STATS="OUTDEGREE";
CREATE VERTEX Card (PRIMARY_ID id STRING, card_number_masked STRING, card_type STRING, status STRING) WITH STATS="OUTDEGREE";
CREATE VERTEX Transaction (PRIMARY_ID id STRING, amount DOUBLE, timestamp STRING, location STRING, device_id STRING, ip_address STRING, is_fraud BOOL, risk_score DOUBLE) WITH STATS="OUTDEGREE";
CREATE VERTEX Merchant (PRIMARY_ID id STRING, name STRING, category STRING, risk_level STRING) WITH STATS="OUTDEGREE";
CREATE VERTEX Device (PRIMARY_ID id STRING, device_token STRING, os_type STRING, is_suspicious BOOL) WITH STATS="OUTDEGREE";
CREATE VERTEX IPAddress (PRIMARY_ID id STRING, ip STRING, country STRING, is_vpn BOOL) WITH STATS="OUTDEGREE";

CREATE UNDIRECTED EDGE HAS_CARD (FROM User, TO Card);
CREATE DIRECTED EDGE PERFORMED_TRANSACTION (FROM User, TO Transaction);
CREATE DIRECTED EDGE USED_CARD (FROM Transaction, TO Card);
CREATE DIRECTED EDGE TRANSACTED_WITH (FROM Transaction, TO Merchant);
CREATE DIRECTED EDGE USED_DEVICE (FROM Transaction, TO Device);
CREATE DIRECTED EDGE USED_IP (FROM Transaction, TO IPAddress);
CREATE DIRECTED EDGE TRANSFERRED_TO (FROM User, TO User, amount DOUBLE, timestamp STRING);

CREATE GRAPH FraudInvestigation(User, Card, Transaction, Merchant, Device, IPAddress, HAS_CARD, PERFORMED_TRANSACTION, USED_CARD, TRANSACTED_WITH, USED_DEVICE, USED_IP, TRANSFERRED_TO);
"""

def get_tigergraph_connection():
    """Initializes and returns a TigerGraphConnection instance."""
    host = os.getenv("TG_HOST", "http://localhost:9000")
    graphname = os.getenv("TG_GRAPH", "FraudInvestigation")
    username = os.getenv("TG_USERNAME", "tigergraph")
    password = os.getenv("TG_PASSWORD", "tigergraph")
    secret = os.getenv("TG_SECRET", "")

    logger.info(f"Connecting to TigerGraph host: {host}, Graph: {graphname}")

    if not HAS_PYTIGERGRAPH:
        return None

    try:
        conn = tg.TigerGraphConnection(
            host=host,
            graphname=graphname,
            username=username,
            password=password,
            gsqlSecret=secret
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to establish pyTigerGraph connection: {e}")
        return None

def create_schema(conn=None):
    """Applies the GSQL Schema to TigerGraph database instance or fallback."""
    if conn is not None:
        try:
            logger.info("Executing GSQL Schema creation on TigerGraph instance...")
            res = conn.gsql(f"USE GLOBAL\n{SCHEMA_GSQL}")
            logger.info(f"Schema creation result: {res}")
            
            # Request secret & token if needed
            secret = conn.createSecret()
            logger.info(f"Generated GSQL Secret: {secret}")
            token = conn.getToken(secret)
            logger.info("TigerGraph Auth Token obtained successfully.")
            return True
        except Exception as e:
            logger.warning(f"Error creating schema on live TigerGraph instance: {e}. Falling back to schema definition file.")
    
    # Save local copy of schema
    schema_dir = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(schema_dir, "schema.gsql")
    with open(schema_file, "w") as f:
        f.write(SCHEMA_GSQL.strip())
    logger.info(f"Saved local GSQL schema definition to {schema_file}")
    return True

if __name__ == "__main__":
    logger.info("Starting Phase 1: TigerGraph Schema Creation...")
    connection = get_tigergraph_connection()
    success = create_schema(connection)
    if success:
        logger.info("Phase 1 Schema creation completed successfully.")
    else:
        logger.error("Phase 1 Schema creation failed.")
        sys.exit(1)
