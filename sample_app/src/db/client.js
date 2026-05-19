const { MongoClient } = require('mongodb');

let client;

async function connectMongo(uri) {
  if (client) return client;
  client = new MongoClient(uri, {
    appName: 'sample-app-oci-mongo-compat',
    retryWrites: true
  });
  await client.connect();
  return client;
}

async function closeMongo() {
  if (client) {
    await client.close();
    client = null;
  }
}

module.exports = {
  connectMongo,
  closeMongo
};
