API Documentation 3 Realtime Updates
____________________________________________________________________________________________________________________________________________________________

Real Time Data Overview

The ProjectX Real Time API utilizes SignalR library (via WebSocket) to provide real-time access to data updates involving accounts, orders, positions, balances and quotes.

There are two hubs: user and market.
he user hub will provide real-time updates to a user's accounts, orders, and positions.
The market hub will provide market data such as market trade events, DOM events, etc.
What is SignalR?

SignalR is a real-time web application framework developed by Microsoft that simplifies the process of adding real-time functionality to web applications. It allows for bidirectional communication between clients (such as web browsers) and servers, enabling features like live chat, notifications, and real-time updates without the need for constant client-side polling or manual handling of connections.

SignalR abstracts away the complexities of real-time communication by providing high-level APIs for developers. It supports various transport protocols, including WebSockets, Server-Sent Events (SSE), Long Polling, and others, automatically selecting the most appropriate transport mechanism based on the capabilities of the client and server.

The framework handles connection management, message routing, and scaling across multiple servers, making it easier for developers to build scalable and responsive web applications. SignalR is available for multiple platforms, including .NET and JavaScript, allowing developers to build real-time applications using their preferred programming languages and frameworks.

Further information on SignalR can be found here.

Example Usage -- User Hub
// Import the necessary modules from @microsoft/signalr
const { HubConnectionBuilder, HttpTransportType } = require('@microsoft/signalr');

// Function to set up and start the SignalR connection
function setupSignalRConnection() {
  const JWT_TOKEN = 'your_bearer_token';
  const SELECTED_ACCOUNT_ID = 123; //your currently selected/visible account ID
  const userHubUrl = 'https://gateway-rtc-demo.s2f.projectx.com/hubs/user?access_token=' + JWT_TOKEN;
  
  // Create the connection
  const rtcConnection = new HubConnectionBuilder()
      .withUrl(userHubUrl, {
          skipNegotiation: true,
          transport: HttpTransportType.WebSockets,
          accessTokenFactory: () => JWT_TOKEN, // Replace with your current JWT token
          timeout: 10000 // Optional timeout
      })
      .withAutomaticReconnect()
      .build();

  // Start the connection
  rtcConnection.start()
      .then(() => {
          // Function to subscribe to the necessary events
          const subscribe = () => {
              rtcConnection.invoke('SubscribeAccounts');
              rtcConnection.invoke('SubscribeOrders', SELECTED_ACCOUNT_ID); //you can call this function multiple times with different account IDs
              rtcConnection.invoke('SubscribePositions', SELECTED_ACCOUNT_ID);  //you can call this function multiple times with different account IDs
              rtcConnection.invoke('SubscribeTrades', SELECTED_ACCOUNT_ID);  //you can call this function multiple times with different account IDs
          };

          // Functions to unsubscribe, if needed
          const unsubscribe = () => {
              rtcConnection.invoke('UnsubscribeAccounts');
              rtcConnection.invoke('UnsubscribeOrders', SELECTED_ACCOUNT_ID); //you can call this function multiple times with different account IDs
              rtcConnection.invoke('UnsubscribePositions', SELECTED_ACCOUNT_ID);  //you can call this function multiple times with different account IDs
              rtcConnection.invoke('UnsubscribeTrades', SELECTED_ACCOUNT_ID);  //you can call this function multiple times with different account IDs

          };

          // Set up the event listeners
          rtcConnection.on('GatewayUserAccount', (data) => {
              console.log('Received account update', data);
          });

          rtcConnection.on('GatewayUserOrder', (data) => {
              console.log('Received order update', data);
          });

          rtcConnection.on('GatewayUserPosition', (data) => {
              console.log('Received position update', data);
          });

          rtcConnection.on('GatewayUserTrade', (data) => {
              console.log('Received trade update', data);
          });

          // Subscribe to the events
          subscribe();

          // Handle reconnection
          rtcConnection.onreconnected((connectionId) => {
              console.log('RTC Connection Reconnected');
              subscribe();
          });
      })
      .catch((err) => {
          console.error('Error starting connection:', err);
      });
}
// Call the function to set up and start the connection
setupSignalRConnection();

Market Hub
// Import the necessary modules from @microsoft/signalr
const { HubConnectionBuilder, HttpTransportType } = require('@microsoft/signalr');

// Function to set up and start the SignalR connection
function setupSignalRConnection() {
  const JWT_TOKEN = 'your_bearer_token';
  const marketHubUrl = 'https://gateway-rtc-demo.s2f.projectx.com/hubs/market?access_token=' + JWT_TOKEN;
  const CONTRACT_ID = 'CON.F.US.RTY.H25'; // Example contract ID

  
  // Create the connection
  const rtcConnection = new HubConnectionBuilder()
      .withUrl(marketHubUrl, {
          skipNegotiation: true,
          transport: HttpTransportType.WebSockets,
          accessTokenFactory: () => JWT_TOKEN, // Replace with your current JWT token
          timeout: 10000 // Optional timeout
      })
      .withAutomaticReconnect()
      .build();

  // Start the connection
  rtcConnection.start()
      .then(() => {
          // Function to subscribe to the necessary events
          const subscribe = () => {
              rtcConnection.invoke('SubscribeContractQuotes', CONTRACT_ID);
              rtcConnection.invoke('SubscribeContractTrades', CONTRACT_ID); 
              rtcConnection.invoke('SubscribeContractMarketDepth', CONTRACT_ID);  
          };

          // Functions to unsubscribe, if needed
          const unsubscribe = () => {
              rtcConnection.invoke('UnsubscribeContractQuotes', CONTRACT_ID); 
              rtcConnection.invoke('UnsubscribeContractTrades', CONTRACT_ID); 
              rtcConnection.invoke('UnsubscribeContractMarketDepth', CONTRACT_ID);  
          };

          // Set up the event listeners
          rtcConnection.on('GatewayQuote', (contractId, data)  => {
              console.log('Received market quote data', data);
          });

          rtcConnection.on('GatewayTrade', (contractId, data) => {
              console.log('Received market trade data', data);
          });

          rtcConnection.on('GatewayDepth', (contractId, data) => {
              console.log('Received market depth data', data);
          });

          // Subscribe to the events
          subscribe();

          // Handle reconnection
          rtcConnection.onreconnected((connectionId) => {
              console.log('RTC Connection Reconnected');
              subscribe();
          });
      })
      .catch((err) => {
          console.error('Error starting connection:', err);
      });
}
// Call the function to set up and start the connection
setupSignalRConnection();


Example Usage -- Market Hub
// Import the necessary modules from @microsoft/signalr
const { HubConnectionBuilder, HttpTransportType } = require('@microsoft/signalr');

function setupSignalRConnection() {
    const JWT_TOKEN = 'your_bearer_token';
    const marketHubUrl = 'https://rtc.topstepx.com/hubs/market?access_token=YOUR_JWT_TOKEN';
    const CONTRACT_ID = 'CON.F.US.RTY.H25';

    const rtcConnection = new HubConnectionBuilder()
        .withUrl(marketHubUrl, {
            skipNegotiation: true,
            transport: HttpTransportType.WebSockets,
            accessTokenFactory: () => JWT_TOKEN,
            timeout: 10000
        })
        .withAutomaticReconnect()
        .build();

    rtcConnection.start()
        .then(() => {
            const subscribe = () => {
                rtcConnection.invoke('SubscribeContractQuotes', CONTRACT_ID);
                rtcConnection.invoke('SubscribeContractTrades', CONTRACT_ID);
                rtcConnection.invoke('SubscribeContractMarketDepth', CONTRACT_ID);
            };

            const unsubscribe = () => {
                rtcConnection.invoke('UnsubscribeContractQuotes', CONTRACT_ID);
                rtcConnection.invoke('UnsubscribeContractTrades', CONTRACT_ID);
                rtcConnection.invoke('UnsubscribeContractMarketDepth', CONTRACT_ID);
            };

            rtcConnection.on('GatewayQuote', (contractId, data)  => {
                console.log('Received market quote data', data);
            });

            rtcConnection.on('GatewayTrade', (contractId, data) => {
                console.log('Received market trade data', data);
            });

            rtcConnection.on('GatewayDepth', (contractId, data) => {
                console.log('Received market depth data', data);
            });

            subscribe();

            rtcConnection.onreconnected((connectionId) => {
                console.log('RTC Connection Reconnected');
                subscribe();
            });
        })
        .catch((err) => {
            console.error('Error starting connection:', err);
        });
}
// Call the function to set up and start the connection
setupSignalRConnection();