# Access Control API
## API Endpoints

### POST /artemis/api/acs/v1/auth/applicationResult
Get status details of applying person information or persons' access level settings to device.
Currently, the returned status details are about applying failure and waiting to be applied.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/acs/v1/auth/applicationResult
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| userId | Optional | String | Header | User ID (1-32 chars, no special chars: ' / \ : * ? " < > \|) |
| applicationResultType | Required | Number | Body | Result type: 1=statistics, 2=error info |
| pageNo | Optional | Number | Body | Page number (1-2147483647), valid when type=2 |
| pageSize | Optional | Number | Body | Records per page (1-500), valid when type=2 |
| type | Required | Number | Body | Access level type: 1=access control, 2=visitor |

**Request Example:**
```json
{
    "applicationResultType": 1,
    "pageNo": 1,
    "pageSize": 2,
    "type": 1
}
```

### POST /artemis/api/acs/v1/door/doControl
Control door operations (open, close, remain open, remain closed) by door ID.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/acs/v1/door/doControl
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| userId | Optional | String | Header | User ID (1-32 chars, no special chars) |
| doorIndexCodes | Required | Array[String] | Body | Access point IDs (max 10) |
| controlType | Required | Number | Body | Control type: 0=remain open, 1=close, 2=open, 3=remain closed |
| controlDirection | Required | Number | Body | Direction: 0=entry, 1=exit |

**Request Example:**
```json
{
    "doorIndexCodes": ["1", "2"],
    "controlType": 3,
    "controlDirection": 0
}
```

### POST /artemis/api/acs/v1/door/events
Search access records by conditions (time, person, access point, event type) with paginated results.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/acs/v1/door/events
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| userId | Optional | String | Header | User ID (1-32 chars, no special chars) |
| eventType | Required | Number | Body | Event type code (see Event Types reference) |
| personName | Optional | String | Body | Person name (1-32 chars, no special chars) |
| doorIndexCodes | Required | Array[String] | Body | Access point IDs (max 10) |
| startTime | Required | String | Body | Start time (ISO 8601: yyyy-MM-ddTHH:mm:ss+TZ) |
| endTime | Required | String | Body | End time (ISO 8601: yyyy-MM-ddTHH:mm:ss+TZ) |
| pageNo | Required | Number | Body | Page number (1-2147483647) |
| pageSize | Required | Number | Body | Records per page (1-500) |
| temperatureStatus | Optional | Number | Body | Temperature: 0=unknown, 1=normal, 2=abnormal |
| wearMaskStatus | Optional | Number | Body | Mask status: 0=unknown, 1=yes, 2=no |
| sortField | Optional | String | Body | Sort field (currently only "SwipeTime") |
| orderType | Optional | Number | Body | Order: 0=ascending, 1=descending (default) |

**Notes:**
- Maximum 31 days between start and end time
- Either eventType or personName must be provided

**Request Example:**
```json
{
    "startTime": "2019-08-26T15:00:00+08:00",
    "endTime": "2019-09-16T15:00:00+08:00",
    "eventType": 197151,
    "personName": "a",
    "doorIndexCodes": ["482"],
    "pageNo": 1,
    "pageSize": 10,
    "temperatureStatus": -1,
    "maskStatus": -1,
    "sortField": "SwipeTime",
    "orderType": 1
}
```

### POST /artemis/api/acs/v1/privilege/group
Get access level list with pagination.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/acs/v1/privilege/group
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| userId | Optional | String | Header | User ID (1-32 chars, no special chars) |
| pageNo | Required | Number | Body | Page number (1-2147483648) |
| pageSize | Required | Number | Body | Records per page (1-500) |
| type | Required | Number | Body | Access level type: 1=access control, 2=visitor |

**Request Example:**
```json
{
    "pageNo": 1,
    "pageSize": 10,
    "type": 1
}
```

### POST /artemis/api/acs/v1/privilege/group/single/addPersons
Assign access levels to persons.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/acs/v1/privilege/group/single/addPersons
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| userId | Optional | String | Header | User ID (1-32 chars, no special chars) |
| privilegeGroupId | Required | String | Body | Access group ID (up to 64 chars) |
| type | Required | Number | Body | Access level type: 1=access control, 2=visitor |
| list | Required | Array[Object] | Body | Person information list |
| list[].id | Required | String | Body | Person/visitor ID (up to 64 chars) |

**Request Example:**
```json
{
    "privilegeGroupId": "1",
    "type": 1,
    "list": [
        {
            "id": "1"
        }
    ]
}
```

### POST /artemis/api/acs/v1/privilege/group/single/deletePersons
Unassign access levels to persons.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/acs/v1/privilege/group/single/deletePersons
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| userId | Optional | String | Header | User ID (1-32 chars, no special chars: ' / \ : * ? " < > \|) |
| privilegeGroupId | Required | String | Body | Access group ID (up to 64 chars) |
| type | Required | Number | Body | Access level type: 1=access control, 2=visitor |
| list | Required | Array[Object] | Body | Person information list |
| list[].id | Required | String | Body | Person/visitor ID (up to 64 chars) |

**Request Example:**
```json
{
    "privilegeGroupId": "1",
    "type": 1,
    "list": [
        {
            "id": "1"
        }
    ]
}
```

### POST /artemis/api/visitor/v1/auth/reapplication
Apply persons' access level settings or information (person ID, person name, face picture, fingerprint, card No., validity, etc. according to device capability) to device when the persons' access level or person information changed.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/visitor/v1/auth/reapplication
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| userId | Optional | String | Header | User ID (1-32 chars, no special chars: ' / \ : * ? " < > \|) |
| orderId | Required | String | Body | Currently not in use |
| ImmediateDownload | Optional | Integer | Body | 0=immediately apply persons including those which have failed, 1=immediately apply persons excluding those which have failed |
| personIds | Optional | String | Body | Person ID list. Multiple items are separated by comma |
| doorIndexCodes | Optional | String | Body | Door ID list. Multiple items are separated by comma |

### POST /artemis/api/visitor/v1/person/ID/elementDownloadDetail
Get the access level application information of a visitor.

**Request URL:**
```
https://[serverAddress]:[serverPort]/artemis/api/visitor/v1/person/ID/elementDownloadDetail
```

**Request Parameters:**
| Parameter | Required | Type | Location | Description |
|-----------|----------|------|----------|-------------|
| id | Required | String | Body | Visitor ID (max 64 chars) |

**Request Example:**
```json
{
    "visitorId": "125"
}
```

