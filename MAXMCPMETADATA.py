from psdi.server import MXServer
from psdi.security import UserInfo
from com.ibm.json.java import JSONObject, JSONArray
from java.sql import Connection
from java.lang import String, Integer, Boolean

mx = MXServer.getMXServer()
ui = mx.getSystemUserInfo()

def runQuery(sql):
    rs = None
    stmt = None
    conn = None
    rows = []
    try:
        conn = mx.getDBManager().getConnection(ui.getConnectionKey())
        stmt = conn.createStatement()
        rs = stmt.executeQuery(sql)
        meta = rs.getMetaData()
        colCount = meta.getColumnCount()

        while rs.next():
            row = {}
            for i in range(1, colCount + 1):
                row[meta.getColumnName(i).lower()] = rs.getObject(i)
            rows.append(row)
    finally:
        if rs: rs.close()
        if stmt: stmt.close()
        if conn: 
            conn.close()
            mx.getDBManager().freeConnection(ui.getConnectionKey())
    return rows


# =========================================================================
# 1. GET ALL OBJECT STRUCTURE DETAILS (OS -> OBJECT)
# =========================================================================
sql_os_objects = """
SELECT INTOBJECTNAME, OBJECTNAME
FROM maximo.MAXINTOBJDETAIL
WHERE INTOBJECTNAME IN (
    SELECT DISTINCT intobjectname
    FROM MAXINTOBJECT
    WHERE USEWITH = 'INTEGRATION' OR USEWITH = 'OSLC'
)
ORDER BY INTOBJECTNAME, OBJECTNAME
"""

osObjectRows = runQuery(sql_os_objects)

# Build mapping
osMap = {}           # OS -> [Objects]
objectToOS = {}      # Object -> [OS]

for row in osObjectRows:
    osName = row["intobjectname"]
    objName = row["objectname"]

    if osName not in osMap:
        osMap[osName] = []
    osMap[osName].append(objName)

    if objName not in objectToOS:
        objectToOS[objName] = []
    objectToOS[objName].append(osName)


# =========================================================================
# 2A. GET OBJECT METADATA (persistent, description, servicename)
# =========================================================================
sql_object_meta = """
SELECT objectname, description, persistent, servicename
FROM MAXOBJECTCFG
WHERE objectname IN (
    SELECT DISTINCT OBJECTNAME
    FROM maximo.MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (
        SELECT DISTINCT intobjectname
        FROM MAXINTOBJECT
        WHERE USEWITH = 'INTEGRATION' OR USEWITH = 'OSLC'
    )
)
ORDER BY objectname
"""

objectMetaRows = runQuery(sql_object_meta)

objectMeta = {}  # objectName -> metadata

for row in objectMetaRows:
    obj = row["objectname"]
    objectMeta[obj] = {
        "description": row["description"],
        "persistent": True if row["persistent"] == 1 else False,
        "servicename": row["servicename"]
    }
    
# =========================================================================
# 2B. GET PRIMARY KEY ATTRIBUTES FOR EACH OBJECT
# =========================================================================
sql_pk = """
SELECT OBJECTNAME, ATTRIBUTENAME, TITLE
FROM MAXATTRIBUTECFG
WHERE REQUIRED = 1
  AND PRIMARYKEYCOLSEQ IS NOT NULL
  AND PERSISTENT = 1 AND 
  OBJECTNAME IN (
    SELECT DISTINCT OBJECTNAME
    FROM maximo.MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (
        SELECT DISTINCT intobjectname
        FROM MAXINTOBJECT
        WHERE USEWITH = 'INTEGRATION' OR USEWITH = 'OSLC'
    )
)
ORDER BY OBJECTNAME, ATTRIBUTENO
"""

pkRows = runQuery(sql_pk)


for row in pkRows:
    obj = row["objectname"]
    if "primaryKeys" not in objectMeta[obj]:
        objectMeta[obj]["primaryKeys"] = []
        
    objectMeta[obj]["primaryKeys"].append({
        "name": row["attributename"],
        "title": row["title"]
    })


# =========================================================================
# 3. GET ATTRIBUTES
# =========================================================================
sql_attributes = """
SELECT 
    a.objectname,
    a.attributename,
    a.domainid,
    d.domaintype,
    a.length,
    a.maxtype,
    a.required,
    a.persistent,
    a.remarks,
    a.title,
    a.attributeno
FROM MAXATTRIBUTECFG a
LEFT JOIN MAXDOMAIN d
  ON a.domainid = d.domainid
WHERE a.objectname IN (
    SELECT DISTINCT OBJECTNAME
    FROM MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (
        SELECT DISTINCT intobjectname
        FROM MAXINTOBJECT
        WHERE USEWITH = 'INTEGRATION' OR USEWITH = 'OSLC'
    )
)
ORDER BY a.objectname, a.attributename
"""

attrRows = runQuery(sql_attributes)

# Attach attributes to object metadata
for row in attrRows:
    obj = row["objectname"]
    if "attributes" not in objectMeta[obj]:
        objectMeta[obj]["attributes"] = []

    attr = {
        "name": row["attributename"],
        "title": row["title"],
        "remarks": row["remarks"],
        "domainId": row["domainid"],
        "domainType": row["domaintype"],
        "length": row["length"],
        "maxtype": row["maxtype"],
        "required": True if row["required"] == 1 else False,
        "persistent": True if row["persistent"] == 1 else False,
        "attributeno": row["attributeno"]
    }
    objectMeta[obj]["attributes"].append(attr)
    
    


# =========================================================================
# 4. GET RELATIONSHIPS
# =========================================================================
sql_relationships = """
SELECT name, parent, child, whereclause, remarks
FROM MAXRELATIONSHIP
WHERE parent IN (
    SELECT DISTINCT OBJECTNAME
    FROM maximo.MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (
        SELECT DISTINCT intobjectname
        FROM MAXINTOBJECT
        WHERE USEWITH = 'INTEGRATION' OR USEWITH = 'OSLC'
    )
)
ORDER BY parent, name
"""

relRows = runQuery(sql_relationships)

# Attach relationships
for row in relRows:
    parent = row["parent"]
    if "relationships" not in objectMeta[parent]:
        objectMeta[parent]["relationships"] = []

    rel = {
        "name": row["name"],
        "target": row["child"],
        "where": row["whereclause"],
        "remarks": row["remarks"]
    }
    objectMeta[parent]["relationships"].append(rel)
    
def toJavaPrimitive(v):
    """Convert Python primitive -> Java primitive safely"""
    if v is None:
        return None
    if isinstance(v, bool):
        return Boolean(v)
    if isinstance(v, int):
        return Integer(v)
    if isinstance(v, float):
        return Double(v)
    # THIS IS THE IMPORTANT FIX
    return String(v)  
    
def toJsonObject(pyDict):
    jobj = JSONObject()
    for k, v in pyDict.items():

        # Handle nested Python list -> JSONArray
        if isinstance(v, list):
            arr = JSONArray()
            for item in v:
                if isinstance(item, dict):
                    arr.add(toJsonObject(item))
                else:
                    arr.add(toJavaPrimitive(item))
            jobj.put(k, arr)

        # Handle nested Python dict -> JSONObject
        elif isinstance(v, dict):
            jobj.put(k, toJsonObject(v))

        # Java-friendly primitive conversion
        elif isinstance(v, bool):
            jobj.put(k, Boolean(v))
        elif isinstance(v, int):
            jobj.put(k, Integer(v))
        else:
            # Strings, None, floats
            jobj.put(k, toJavaPrimitive(v) if v is not None else None)

    return jobj

# =========================================================================
# 5. ASSEMBLE FINAL JSON
# =========================================================================
result = JSONObject()

# OS -> objects
osJson = JSONObject()
for osName, objs in osMap.items():
    arr = JSONArray()
    for o in objs:
        arr.add(o)
    osJson.put(osName, arr)
result.put("object_structures", osJson)

# Objects -> metadata
objectJson = JSONObject()
for obj, meta in objectMeta.items():
    j = JSONObject()

    # Basic metadata
    j.put("description", meta.get("description"))
    j.put("persistent", meta.get("persistent"))
    j.put("servicename", meta.get("servicename"))
    

    pkJsonArray = JSONArray()
    for pk in meta.get("primaryKeys",[]):
        pkJson = JSONObject()
        pkJson.put("name", pk.get("name"))
        pkJson.put("title", pk.get("title"))
        pkJsonArray.add(pkJson)

    j.put("primaryKeys",pkJsonArray)
    
   

    # OS list
    osArr = JSONArray()
    for osName in objectToOS.get(obj, []):
        osArr.add(osName)
    j.put("included_in_os", osArr)

    # Attributes
    attrArr = JSONArray()
    for a in meta.get("attributes", []):
        attrArr.add(toJsonObject(a))
    j.put("attributes", attrArr)

    # Relationships
    relArr = JSONArray()
    for r in meta.get("relationships", []):
        relArr.add(toJsonObject(r))
    j.put("relationships", relArr)

    objectJson.put(obj, j)

result.put("objects", objectJson)

responseBody = result.serialize()
