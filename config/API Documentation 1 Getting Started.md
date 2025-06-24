API Documentation 1 Getting Started 
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Authenticate
This section outlines the process of authenticating API requests using JSON Web Tokens.
____________________________________________________________________________________________________________________________________________________________
Authenticate (with API key)
We utilize JSON Web Tokens to authenticate all requests sent to the API. This process involves obtaining a session token, which is required for future requests.

Step 1

To begin, ensure you have the following:

An API key obtained from your firm. If you do not have these credentials, please contact your firm.
The connection URLs, obtained here.
Step 2

API Reference: Login API

Create a POST request with your username and API key.

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Auth/loginKey' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "userName": "string",
  "apiKey": "string"
}'

Step 3

Process the API response, and make sure the result is Success (0), then store your session token in a safe place. This session token will grant full access to the Gateway API.

Response
{
    "token": "your_session_token_here",
    "success": true,
    "errorCode": 0,
    "errorMessage": null
}

Notes

All further requests will require you to provide the session token in the "Authorization" HTTP header using the Bearer method.

Session tokens are only valid for 24 hours. You must revalidate your token to continue using the same session.
____________________________________________________________________________________________________________________________________________________________
Authenticate (with API key)

We utilize JSON Web Tokens to authenticate all requests sent to the API. This process involves obtaining a session token, which is required for future requests.

Step 1

To begin, ensure you have the following:

An API key obtained from your firm. If you do not have these credentials, please contact your firm.
The connection URLs, obtained here.
Step 2

API Reference: Login API

Create a POST request with your username and API key.

cURL Request
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Auth/loginKey' \
  -H 'accept: text/plain' \
  -H 'Content-Type: application/json' \
  -d '{
  "userName": "string",
  "apiKey": "string"
}'

Step 3

Process the API response, and make sure the result is Success (0), then store your session token in a safe place. This session token will grant full access to the Gateway API.

Response
{
    "token": "your_session_token_here",
    "success": true,
    "errorCode": 0,
    "errorMessage": null
}

Notes

All further requests will require you to provide the session token in the "Authorization" HTTP header using the Bearer method.

Session tokens are only valid for 24 hours. You must revalidate your token to continue using the same session.
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Validate Session
Once you have successfully authenticated, session tokens are only valid for 24 hours.
If your token has expired, you must re-validate it to receive a new token.

Validate Token

API Reference: Validate Session API

To validate your token, you must make a POST request to the endpoint referenced above.

cURL
Response
curl -X 'POST' \
  'https://gateway-api-demo.s2f.projectx.com/api/Auth/validate' \
  -H 'accept: text/plain' \
  -d ''

Final Step

Replace your existing JSON Web Tokens and continue making HTTP calls.
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Placing Your First Order
This documentation outlines the process for placing your first order using our API. To successfully execute an order, you must have an active trading account associated with your user. Follow the steps below to retrieve your account details, browse available contracts, and place your order.

Step 1

To initiate the order process, you must first retrieve a list of active accounts linked to your user. This step is essential for confirming your account status before placing an order.

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/account/search

API Reference: /api/account/search

Request
Response
cURL Request
{
  "onlyActiveAccounts": true
}       

Step 2

Once you have identified your active accounts, the next step is to retrieve a list of contracts available for trading. This information will assist you in choosing the appropriate contracts for your order.

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/contract/search

API Reference: /api/contract/search

Request
Response
cURL Request
{
  "live": false,
  "searchText": "NQ"
}                    

Final Step

Having noted your account ID and the selected contract ID, you are now ready to place your order. Ensure that you provide accurate details to facilitate a successful transaction.

API URL: POST https://gateway-api-demo.s2f.projectx.com/api/order/place

API Reference: /api/order/place

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
Request
Response
cURL Request
{     
  "accountId": 1,
  "contractId": "CON.F.US.DA6.M25",
  "type": 2,
  "side": 1,
  "size": 1,
  "limitPrice": null,
  "stopPrice": null,
  "trailPrice": null,
  "customTag": null,
  "linkedOrderId": null
}                     
____________________________________________________________________________________________________________________________________________________________
____________________________________________________________________________________________________________________________________________________________
Connection URLs

Select an Environment: TopstepX
Connection Details:
API Endpoint: https://api.topstepx.com
User Hub: https://rtc.topstepx.com/hubs/user
Market Hub: https://rtc.topstepx.com/hubs/market
