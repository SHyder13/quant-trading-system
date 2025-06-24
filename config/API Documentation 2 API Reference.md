API Documentation 2 API Reference 
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Account
____________________________________________________________________________________________________________________________________________________________
Search for Account
API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Account/search

API Reference: /api/account/search

Description

Search for accounts.

Parameters

Name	Type	Description	Required	Nullable
onlyActiveAccounts	boolean	Whether to filter only active accounts.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Account/search' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "onlyActiveAccounts": true
}'

Example Response

Success
Error
{
  "accounts": [
      {
          "id": 1,
          "name": "TEST_ACCOUNT_1",
          "balance": 50000,
          "canTrade": true,
          "isVisible": true
      }
  ],
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                      
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Market Data
Authorized users have access to order operations, allowing them to search for, modify, place, and cancel orders.
____________________________________________________________________________________________________________________________________________________________
Retrieve Bars

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/History/retrieveBars

API Reference: /api/history/retrieveBars

Description

Retrieve bars.

Parameters

Name	Type	Description	Required	Nullable
contractId	integer	The contract ID.	Required	false
live	boolean	Whether to retrieve bars using the sim or live data subscription.	Required	false
startTime	datetime	The start time of the historical data.	Required	false
endTime	datetime	The end time of the historical data.	Required	false
unit	integer	The unit of aggregation for the historical data:
1 = Second
2 = Minute
3 = Hour
4 = Day
5 = Week
6 = Month	Required	false
unitNumber	integer	The number of units to aggregate.	Required	false
limit	integer	The maximum number of bars to retrieve.	Required	false
includePartialBar	boolean	Whether to include a partial bar representing the current time unit.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/History/retrieveBars' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
    "contractId": "CON.F.US.RTY.Z24",
    "live": false,
    "startTime": "2024-12-01T00:00:00Z",
    "endTime": "2024-12-31T21:00:00Z",
    "unit": 3,
    "unitNumber": 1,
    "limit": 7,
    "includePartialBar": false
  }'

Example Response

Success
Error
{
    "bars": [
        {
            "t": "2024-12-20T14:00:00+00:00",
            "o": 2208.100000000,
            "h": 2217.000000000,
            "l": 2206.700000000,
            "c": 2210.100000000,
            "v": 87
        },
        {
            "t": "2024-12-20T13:00:00+00:00",
            "o": 2195.800000000,
            "h": 2215.000000000,
            "l": 2192.900000000,
            "c": 2209.800000000,
            "v": 536
        },
        {
            "t": "2024-12-20T12:00:00+00:00",
            "o": 2193.600000000,
            "h": 2200.300000000,
            "l": 2192.000000000,
            "c": 2198.000000000,
            "v": 180
        },
        {
            "t": "2024-12-20T11:00:00+00:00",
            "o": 2192.200000000,
            "h": 2194.800000000,
            "l": 2189.900000000,
            "c": 2194.800000000,
            "v": 174
        },
        {
            "t": "2024-12-20T10:00:00+00:00",
            "o": 2200.400000000,
            "h": 2200.400000000,
            "l": 2191.000000000,
            "c": 2193.100000000,
            "v": 150
        },
        {
            "t": "2024-12-20T09:00:00+00:00",
            "o": 2205.000000000,
            "h": 2205.800000000,
            "l": 2198.900000000,
            "c": 2200.500000000,
            "v": 56
        },
        {
            "t": "2024-12-20T08:00:00+00:00",
            "o": 2207.700000000,
            "h": 2210.100000000,
            "l": 2198.100000000,
            "c": 2204.900000000,
            "v": 144
        }
    ],
    "success": true,
    "errorCode": 0,
    "errorMessage": null
}

Example Response Error
Error: response status is 401

___________________________________________________________________________________________________________________________
Search for Contracts
API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Contract/search

API Reference: /api/contract/search

Description

Search for contracts.

Parameters

Name	Type	Description	Required	Nullable
searchText	string	The name of the contract to search for.	Required	false
live	boolean	Whether to search for contracts using the sim/live data subscription.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Contract/search' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "live": false,
  "searchText": "NQ"
}'

Example Response

Success
Error
{
  "contracts": [
      {
          "id": "CON.F.US.ENQ.H25",
          "name": "ENQH25",
          "description": "E-mini NASDAQ-100: March 2025",
          "tickSize": 0.25,
          "tickValue": 5,
          "activeContract": true
      },
      {
          "id": "CON.F.US.MNQ.H25",
          "name": "MNQH25",
          "description": "Micro E-mini Nasdaq-100: March 2025",
          "tickSize": 0.25,
          "tickValue": 0.5,
          "activeContract": true
      },
      {
          "id": "CON.F.US.NQG.G25",
          "name": "NQGG25",
          "description": "E-Mini Natural Gas: February 2025",
          "tickSize": 0.005,
          "tickValue": 12.5,
          "activeContract": true
      },
      {
          "id": "CON.F.US.NQM.G25",
          "name": "NQMG25",
          "description": "E-Mini Crude Oil: February 2025",
          "tickSize": 0.025,
          "tickValue": 12.5,
          "activeContract": true
      }
  ],
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}
____________________________________________________________________________________________________________________________________________________________
Search for Contract by Id

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Contract/searchById

API Reference: /api/contract/searchbyid

Description

Search for contracts.

Parameters

Name	Type	Description	Required	Nullable
contractId	string	The id of the contract to search for.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Contract/searchById' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "contractId": "CON.F.US.ENQ.H25"
}'

Example Response

Success
Error
{
  "contracts": [
      {
          "id": "CON.F.US.ENQ.H25",
          "name": "ENQH25",
          "description": "E-mini NASDAQ-100: March 2025",
          "tickSize": 0.25,
          "tickValue": 5,
          "activeContract": true
      }
  ],
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}             
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Orders
Authorized users have access to order operations, allowing them to search for, modify, place, and cancel orders.
____________________________________________________________________________________________________________________________________________________________
Search for Orders

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Order/search

API Reference: /api/order/search

Description

Search for orders.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
startTimestamp	datetime	The start of the timestamp filter.	Required	false
endTimestamp	datetime	The end of the timestamp filter.	Optional	true
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Order/search' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 202,
  "startTimestamp": "2024-12-30T16:48:16.003Z",
  "endTimestamp": "2025-12-30T16:48:16.003Z"
}'

Example Response

Success
Error
{
  "orders": [
      {
          "id": 26060,
          "accountId": 545,
          "contractId": "CON.F.US.EP.M25",
          "creationTimestamp": "2025-04-14T17:49:10.142532+00:00",
          "updateTimestamp": null,
          "status": 2,
          "type": 2,
          "side": 0,
          "size": 1,
          "limitPrice": null,
          "stopPrice": null
      },
      {
          "id": 26062,
          "accountId": 545,
          "contractId": "CON.F.US.EP.M25",
          "creationTimestamp": "2025-04-14T17:49:53.043234+00:00",
          "updateTimestamp": null,
          "status": 2,
          "type": 2,
          "side": 1,
          "size": 1,
          "limitPrice": null,
          "stopPrice": null
      }
  ],
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                         
____________________________________________________________________________________________________________________________________________________________
Search for Open Orders

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Order/searchOpen

API Reference: /api/order/searchopen

Description

Search for open orders.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Order/searchOpen' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 212
}'

Example Response

Success
Error
{
  "orders": [
      {
          "id": 26970,
          "accountId": 212,
          "contractId": "CON.F.US.EP.M25",
          "creationTimestamp": "2025-04-21T19:45:52.105808+00:00",
          "updateTimestamp": "2025-04-21T19:45:52.105808+00:00",
          "status": 1,
          "type": 4,
          "side": 1,
          "size": 1,
          "limitPrice": null,
          "stopPrice": 5138.000000000
      }
  ],
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}
____________________________________________________________________________________________________________________________________________________________
Place an Order

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Order/place

API Reference: /api/order/place

Description

Place an order.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
contractId	string	The contract ID.	Required	false
type	integer	The order type:
1 = Limit
2 = Market
4 = Stop
5 = TrailingStop
6 = JoinBid
7 = JoinAsk	Required	false
side	integer	The side of the order:
0 = Bid (buy)
1 = Ask (sell)	Required	false
size	integer	The size of the order.	Required	false
limitPrice	decimal	The limit price for the order, if applicable.	Optional	true
stopPrice	decimal	The stop price for the order, if applicable.	Optional	true
trailPrice	decimal	The trail price for the order, if applicable.	Optional	true
customTag	string	An optional custom tag for the order.	Optional	true
linkedOrderId	integer	The linked order id.	Optional	true
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Order/place' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 465,
  "contractId": "CON.F.US.DA6.M25",
  "type": 2,
  "side": 1,
  "size": 1,
  "limitPrice": null,
  "stopPrice": null,
  "trailPrice": null,
  "customTag": null,
  "linkedOrderId": null
}'

Example Response

Success
Error
{
  "orderId": 9056,
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                         
____________________________________________________________________________________________________________________________________________________________
Cancel an Order

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Order/cancel

API Reference: /api/order/cancel

Description

Cancel an order.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
orderId	integer	The order id.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Order/cancel' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 465,
  "orderId": 26974
}'

Example Response

Success
Error
{
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                
____________________________________________________________________________________________________________________________________________________________
Modify an Order

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Order/modify

API Reference: /api/order/modify

Description

Modify an open order.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
orderId	integer	The order id.	Required	false
size	integer	The size of the order.	Optional	true
limitPrice	decimal	The limit price for the order, if applicable.	Optional	true
stopPrice	decimal	The stop price for the order, if applicable.	Optional	true
trailPrice	decimal	The trail price for the order, if applicable.	Optional	true
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Order/modify' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 465,
  "orderId": 26974,
  "size": 1,
  "limitPrice": null,
  "stopPrice": 1604,
  "trailPrice": null
}
'

Example Response

Success
Error
{
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                   
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________ 
Positions
Authorized users have access to position operations, allowing them to search for, and close positions.
____________________________________________________________________________________________________________________________________________________________
Close Positions

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Position/closeContract

API Reference: /api/position/closeContract

Description

Close a position.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
contractId	string	The contract ID.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Position/closeContract' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 536,
  "contractId": "CON.F.US.GMET.J25"
}'

Example Response

Success
Error
{
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                      
____________________________________________________________________________________________________________________________________________________________
Partially Close Positions

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Position/partialCloseContract

API Reference: /api/position/partialclosecontract

Description

Partially close a position.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
contractId	string	The contract ID.	Required	false
size	integer	The size to close.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Position/partialCloseContract' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 536,
  "contractId": "CON.F.US.GMET.J25",
  "size": 1
}'

Example Response

Success
Error
{
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                    
____________________________________________________________________________________________________________________________________________________________
Search for Positions

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Position/searchOpen

API Reference: /api/position/searchOpen

Description

Search for open positions.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Position/searchOpen' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 536
}'

Example Response

Success
Error
{
  "positions": [
      {
          "id": 6124,
          "accountId": 536,
          "contractId": "CON.F.US.GMET.J25",
          "creationTimestamp": "2025-04-21T19:52:32.175721+00:00",
          "type": 1,
          "size": 2,
          "averagePrice": 1575.750000000
      }
  ],
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}               
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Trades

Authorized users have access to trade operations, allowing them to search for trades.
____________________________________________________________________________________________________________________________________________________________
Search for Trades

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/Trade/search

API Reference: /api/Trade/search

Description

Search for trades from the request parameters.

Parameters

Name	Type	Description	Required	Nullable
accountId	integer	The account ID.	Required	false
startTimestamp	datetime	The start of the timestamp filter.	Required	false
endTimestamp	datetime	The end of the timestamp filter.	Optional	true
Example Usage

Example Request

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Trade/search' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "accountId": 203,
  "startTimestamp": "2025-01-20T15:47:39.882Z",
  "endTimestamp": "2025-01-30T15:47:39.882Z"
}'

Example Response

Success
Error
{
  "trades": [
      {
          "id": 8604,
          "accountId": 203,
          "contractId": "CON.F.US.EP.H25",
          "creationTimestamp": "2025-01-21T16:13:52.523293+00:00",
          "price": 6065.250000000,
          "profitAndLoss": 50.000000000,
          "fees": 1.4000,
          "side": 1,
          "size": 1,
          "voided": false,
          "orderId": 14328
      },
      {
          "id": 8603,
          "accountId": 203,
          "contractId": "CON.F.US.EP.H25",
          "creationTimestamp": "2025-01-21T16:13:04.142302+00:00",
          "price": 6064.250000000,
          "profitAndLoss": null,    //a null value indicates a half-turn trade
          "fees": 1.4000,
          "side": 0,
          "size": 1,
          "voided": false,
          "orderId": 14326
      }
  ],
  "success": true,
  "errorCode": 0,
  "errorMessage": null
}                 
