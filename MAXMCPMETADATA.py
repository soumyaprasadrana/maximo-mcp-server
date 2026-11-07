from psdi.server import MXServer
from psdi.security import UserInfo
from com.ibm.json.java import JSONObject, JSONArray
from java.sql import Connection
from java.lang import String, Integer, Boolean, Double, System

# The MCP server reads this line from the script source to know which parameters this
# version understands. Keep it on its own line.
MCP_METADATA_CONTRACT = 2

# -----------------------------------------------------------------------------------------
# Parameters (all optional; GET /api/script/MAXMCPMETADATA?...)
#
#   (none)                    full payload: every object structure and every member object,
#                             exactly as the original script returned it
#   mode=catalog              object_structures only (object structure -> member objects)
#   mode=os&os=A,B            object_structures + objects for those object structures
#   mode=object&objects=X,Y   objects by name (any object, not only object-structure members);
#                             object_structures is empty
#
# Names are validated against [A-Z0-9_], 1-30 characters, and bound as PreparedStatement parameters --
# never concatenated into SQL. This script runs with the system user's connection.
# Every response carries _meta: { contract, mode, serverTime }.
# -----------------------------------------------------------------------------------------

mx = MXServer.getMXServer()
ui = mx.getSystemUserInfo()

NAME_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
MAX_NAMES = 200


def isValidName(n):
    # ^[A-Z0-9_]{1,30}$ without the re module (not every Maximo Jython ships it).
    if len(n) < 1 or len(n) > 30:
        return False
    for ch in n:
        if ch not in NAME_CHARS:
            return False
    return True


def getParam(name):
    try:
        v = request.getQueryParam(name)
    except:
        v = None
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    return v


def parseNames(raw):
    names = []
    if not raw:
        return names
    for part in raw.split(","):
        n = part.strip().upper()
        if not n:
            continue
        if not isValidName(n):
            raise ValueError("invalid name: " + n)
        if n not in names:
            names.append(n)
    if len(names) > MAX_NAMES:
        raise ValueError("too many names (max " + str(MAX_NAMES) + ")")
    return names


def placeholders(values):
    return ",".join(["?"] * len(values))


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

# A system property, not caller input -- but it is still passed as bound parameters.
useWithIn = placeholders(useWithValues)


def runQuery(sql, params=None):
    rs = None
    stmt = None
    conn = None
    rows = []

    try:
        conn = mx.getDBManager().getConnection(ui.getConnectionKey())
        stmt = conn.prepareStatement(sql)
        if params:
            for i in range(len(params)):
                stmt.setString(i + 1, params[i])
        rs = stmt.executeQuery()
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


def metaBlock(mode):
    m = JSONObject()
    m.put("contract", Integer(MCP_METADATA_CONTRACT))
    m.put("mode", mode)
    m.put("serverTime", String(str(System.currentTimeMillis())))
    return m


def errorResponse(mode, message):
    result = JSONObject()
    result.put("_meta", metaBlock(mode))
    result.put("error", message)
    return result.serialize()


# -----------------------------------------------------------------------------------------
# Scope: which object structures / objects this call covers. Each piece is a SQL fragment
# plus its bound parameters, so the four queries below stay identical to the original
# script in the default (full) mode.
# -----------------------------------------------------------------------------------------
OS_SUBQUERY = """
    SELECT DISTINCT intobjectname
    FROM MAXINTOBJECT
    WHERE USEWITH IN (""" + useWithIn + """)"""


def buildScope(mode, osNames, objectNames):
    if mode == "os":
        osSub = OS_SUBQUERY + " AND INTOBJECTNAME IN (" + placeholders(osNames) + ")"
        osParams = useWithValues + osNames
        objFilter = """
    SELECT DISTINCT OBJECTNAME
    FROM MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (""" + osSub + """
    )"""
        return osSub, osParams, objFilter, osParams
    if mode == "object":
        return OS_SUBQUERY, list(useWithValues), placeholders(objectNames), list(objectNames)
    # full / catalog
    objFilter = """
    SELECT DISTINCT OBJECTNAME
    FROM MAXINTOBJDETAIL
    WHERE INTOBJECTNAME IN (""" + OS_SUBQUERY + """
    )"""
    return OS_SUBQUERY, list(useWithValues), objFilter, list(useWithValues)


def main():
    mode = (getParam("mode") or "full").lower()
    if mode not in ("full", "catalog", "os", "object"):
        return errorResponse(mode, "unknown mode: " + mode)

    try:
        osNames = parseNames(getParam("os")) if mode == "os" else []
        objectNames = parseNames(getParam("objects")) if mode == "object" else []
    except ValueError, e:
        return errorResponse(mode, str(e))
    if mode == "os" and not osNames:
        return errorResponse(mode, "mode=os needs os=<name>[,<name>...]")
    if mode == "object" and not objectNames:
        return errorResponse(mode, "mode=object needs objects=<name>[,<name>...]")

    osSub, osParams, objFilter, objParams = buildScope(mode, osNames, objectNames)

    # =====================================================================
    # 1. OBJECT STRUCTURE DETAILS (OS -> OBJECT)
    # =====================================================================
    osMap = {}
    objectToOS = {}

    if mode != "object":
        osObjectRows = runQuery("""
SELECT INTOBJECTNAME, OBJECTNAME
FROM MAXINTOBJDETAIL
WHERE INTOBJECTNAME IN (""" + osSub + """
)
ORDER BY INTOBJECTNAME, OBJECTNAME
""", osParams)

        for row in osObjectRows:
            osName = row["intobjectname"]
            objName = row["objectname"]
            if osName not in osMap:
                osMap[osName] = []
            osMap[osName].append(objName)
            if mode == "full":
                if objName not in objectToOS:
                    objectToOS[objName] = []
                objectToOS[objName].append(osName)

    if mode == "catalog":
        result = JSONObject()
        result.put("_meta", metaBlock(mode))
        osJson = JSONObject()
        for osName, objs in osMap.items():
            arr = JSONArray()
            for o in objs:
                arr.add(o)
            osJson.put(osName, arr)
        result.put("object_structures", osJson)
        return result.serialize()

    if mode in ("os", "object"):
        # included_in_os for the objects in scope, across ALL valid object structures (not
        # only the requested ones), so a partial reload does not shrink it.
        rows = runQuery("""
SELECT INTOBJECTNAME, OBJECTNAME
FROM MAXINTOBJDETAIL
WHERE OBJECTNAME IN (""" + objFilter + """
)
  AND INTOBJECTNAME IN (""" + OS_SUBQUERY + """
)
ORDER BY INTOBJECTNAME, OBJECTNAME
""", objParams + useWithValues)
        for row in rows:
            objName = row["objectname"]
            if objName not in objectToOS:
                objectToOS[objName] = []
            objectToOS[objName].append(row["intobjectname"])

    # =====================================================================
    # 2A. OBJECT METADATA
    # =====================================================================
    objectMetaRows = runQuery("""
SELECT objectname, description, persistent, servicename, EXTENDSOBJECT
FROM MAXOBJECTCFG
WHERE objectname IN (""" + objFilter + """
)
ORDER BY objectname
""", objParams)

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

    # =====================================================================
    # 2B. PRIMARY KEY ATTRIBUTES
    # =====================================================================
    pkRows = runQuery("""
SELECT OBJECTNAME, ATTRIBUTENAME, TITLE
FROM MAXATTRIBUTECFG
WHERE REQUIRED = 1
  AND PRIMARYKEYCOLSEQ IS NOT NULL
  AND PERSISTENT = 1
  AND OBJECTNAME IN (""" + objFilter + """
)
ORDER BY OBJECTNAME, ATTRIBUTENO
""", objParams)

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

    # =====================================================================
    # 3. ATTRIBUTES
    # =====================================================================
    attrRows = runQuery("""
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
WHERE a.objectname IN (""" + objFilter + """
)
ORDER BY a.objectname, a.attributename
""", objParams)

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

    # =====================================================================
    # 4. RELATIONSHIPS
    # =====================================================================
    relRows = runQuery("""
SELECT name, parent, child, whereclause, remarks
FROM MAXRELATIONSHIP
WHERE parent IN (""" + objFilter + """
)
ORDER BY parent, name
""", objParams)

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

    # =====================================================================
    # 5. ASSEMBLE FINAL JSON
    # =====================================================================
    result = JSONObject()
    result.put("_meta", metaBlock(mode))

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
    return result.serialize()


responseBody = main()
