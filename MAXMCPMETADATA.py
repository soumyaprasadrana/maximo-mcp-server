from psdi.server import MXServer
from psdi.security import UserInfo
from com.ibm.json.java import JSONObject, JSONArray
from java.sql import Connection
from java.lang import String, Integer, Boolean, Double

mx = MXServer.getMXServer()
ui = mx.getSystemUserInfo()

# =========================================================================
# 0. GET VALID OBJECT STRUCTURE USEWITH VALUES
# =========================================================================
validUseWith = mx.getProperty("mxe.oslc.validusewith")

if validUseWith is None or not str(validUseWith).strip():
    validUseWith = "INTEGRATION,OSLC"

useWithValues = [
    value.strip().upper()
    for value in str(validUseWith).split(",")
    if value and value.strip()
]

# Example: 'OSLC','INTEGRATION','REPORTING','MIGRATIONMGR'
useWithInClause = ",".join(
    ["'" + value.replace("'", "''") + "'" for value in useWithValues]
)

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
        if rs:
            rs.close()
        if stmt:
            stmt.close()
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
    WHERE USEWITH IN (""" + useWithInClause + """)
)
ORDER BY INTOBJECTNAME, OBJECTNAME
"""

osObjectRows = runQuery(sql_os_objects)

osMap = {}
objectToOS = {}

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
# 2A. GET OBJECT METADATA
# =========================================================================
sql_object_meta = """
SELECT objectname, description, persistent, servicename, EXTENDSOBJECT
FROM MAXOBJECTCFG
WHERE objectname IN (
    SELECT DISTINCT OBJECTNAME
    FROM maximo.MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (
        SELECT DISTINCT intobjectname
        FROM MAXINTOBJECT
        WHERE USEWITH IN (""" + useWithInClause + """)
    )
)
ORDER BY objectname
"""

objectMetaRows = runQuery(sql_object_meta)

objectMeta = {}

for row in objectMetaRows:
    obj = row["objectname"]
    ext = row.get("extendsoBject")
    if ext is None:
        ext = row.get("extendsobject")
    if ext is None:
        ext = row.get("EXTENDSOBJECT")
    extName = str(ext).strip().upper() if ext else None
    if not extName:
        extName = None
    objectMeta[obj] = {
        "description": row["description"],
        "persistent": True if row["persistent"] == 1 else False,
        "servicename": row["servicename"],
        "extendsObject": extName
    }


# =========================================================================
# 2B. GET PRIMARY KEY ATTRIBUTES
# =========================================================================
sql_pk = """
SELECT OBJECTNAME, ATTRIBUTENAME, TITLE
FROM MAXATTRIBUTECFG
WHERE REQUIRED = 1
  AND PRIMARYKEYCOLSEQ IS NOT NULL
  AND PERSISTENT = 1
  AND OBJECTNAME IN (
    SELECT DISTINCT OBJECTNAME
    FROM maximo.MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (
        SELECT DISTINCT intobjectname
        FROM MAXINTOBJECT
        WHERE USEWITH IN (""" + useWithInClause + """)
    )
)
ORDER BY OBJECTNAME, ATTRIBUTENO
"""

pkRows = runQuery(sql_pk)

for row in pkRows:
    obj = row["objectname"]

    if obj not in objectMeta:
        continue

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
        WHERE USEWITH IN (""" + useWithInClause + """)
    )
)
ORDER BY a.objectname, a.attributename
"""

attrRows = runQuery(sql_attributes)

for row in attrRows:
    obj = row["objectname"]

    if obj not in objectMeta:
        continue

    if "attributes" not in objectMeta[obj]:
        objectMeta[obj]["attributes"] = []

    objectMeta[obj]["attributes"].append({
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
    })


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
        WHERE USEWITH IN (""" + useWithInClause + """)
    )
)
ORDER BY parent, name
"""

relRows = runQuery(sql_relationships)

for row in relRows:
    parent = row["parent"]

    if parent not in objectMeta:
        continue

    if "relationships" not in objectMeta[parent]:
        objectMeta[parent]["relationships"] = []

    objectMeta[parent]["relationships"].append({
        "name": row["name"],
        "target": row["child"],
        "where": row["whereclause"],
        "remarks": row["remarks"]
    })


def toJavaPrimitive(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return Boolean(v)
    if isinstance(v, int):
        return Integer(v)
    if isinstance(v, float):
        return Double(v)
    return String(v)


def toJsonObject(pyDict):
    jobj = JSONObject()

    for k, v in pyDict.items():
        if isinstance(v, list):
            arr = JSONArray()
            for item in v:
                if isinstance(item, dict):
                    arr.add(toJsonObject(item))
                else:
                    arr.add(toJavaPrimitive(item))
            jobj.put(k, arr)

        elif isinstance(v, dict):
            jobj.put(k, toJsonObject(v))

        elif isinstance(v, bool):
            jobj.put(k, Boolean(v))

        elif isinstance(v, int):
            jobj.put(k, Integer(v))

        else:
            jobj.put(k, toJavaPrimitive(v) if v is not None else None)

    return jobj


# =========================================================================
# 5. ASSEMBLE FINAL JSON
# =========================================================================
result = JSONObject()

osJson = JSONObject()

for osName, objs in osMap.items():
    arr = JSONArray()
    for o in objs:
        arr.add(o)
    osJson.put(osName, arr)

result.put("object_structures", osJson)

objectJson = JSONObject()

for obj, meta in objectMeta.items():
    j = JSONObject()

    j.put("description", meta.get("description"))
    j.put("persistent", meta.get("persistent"))
    j.put("servicename", meta.get("servicename"))
    ext = meta.get("extendsObject")
    j.put("extendsObject", String(ext) if ext else None)

    pkJsonArray = JSONArray()
    for pk in meta.get("primaryKeys", []):
        pkJson = JSONObject()
        pkJson.put("name", pk.get("name"))
        pkJson.put("title", pk.get("title"))
        pkJsonArray.add(pkJson)

    j.put("primaryKeys", pkJsonArray)

    osArr = JSONArray()
    for osName in objectToOS.get(obj, []):
        osArr.add(osName)

    j.put("included_in_os", osArr)

    attrArr = JSONArray()
    for a in meta.get("attributes", []):
        attrArr.add(toJsonObject(a))

    j.put("attributes", attrArr)

    relArr = JSONArray()
    for r in meta.get("relationships", []):
        relArr.add(toJsonObject(r))

    j.put("relationships", relArr)

    objectJson.put(obj, j)

result.put("objects", objectJson)

responseBody = result.serialize()