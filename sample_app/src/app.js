require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const { connectMongo, closeMongo } = require('./db/client');
const { createExamplesRouter } = require('./routes/examples');

async function bootstrap() {
  const port = Number(process.env.PORT || 3000);
  const mongoUri = process.env.MONGODB_URI || 'mongodb://localhost:27017';
  const mongoDbName = process.env.MONGODB_DB || 'sample_app';
  const collectionName = process.env.MONGODB_COLLECTION || 'orders';

  // Intentionally include Mongoose in the app to exercise driver/wrapper detection.
  // We do not require a separate Mongoose connection for this validation sample.
  void mongoose.modelNames();

  const client = await connectMongo(mongoUri);
  const db = client.db(mongoDbName);
  const collection = db.collection(collectionName);

  await collection.createIndex({ location: '2dsphere' });

  const app = express();
  app.use(express.json());

  app.get('/health', (_req, res) => {
    res.json({ ok: true, service: 'sample-app-oci-mongo-compat' });
  });

  app.use('/examples', createExamplesRouter({ db, collection }));

  const server = app.listen(port, () => {
    console.log(`sample_app running on port ${port}`);
  });

  const shutdown = async () => {
    server.close(async () => {
      await closeMongo();
      process.exit(0);
    });
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

bootstrap().catch((err) => {
  console.error('failed_to_bootstrap', err);
  process.exit(1);
});
