const express = require('express');
const {
  runIncompatibleExamples,
  buildUnsupportedFindFilter,
  buildUnsupportedUpdateDoc,
  buildUnsupportedPipeline,
  buildUnsupportedCommands,
  buildUnsupportedBsonTypeExamples
} = require('../services/incompatibleExamples');

function createExamplesRouter({ db, collection }) {
  const router = express.Router();

  router.get('/preview', async (_req, res) => {
    res.json({
      queryExample: buildUnsupportedFindFilter(),
      updateExample: buildUnsupportedUpdateDoc(),
      pipelineExample: buildUnsupportedPipeline(),
      commandsExample: buildUnsupportedCommands().slice(0, 5),
      bsonTypeExample: buildUnsupportedBsonTypeExamples()
    });
  });

  router.post('/run', async (_req, res) => {
    try {
      const report = await runIncompatibleExamples(db, collection);
      res.json(report);
    } catch (err) {
      res.status(500).json({
        error: 'failed_to_run_examples',
        message: err.message
      });
    }
  });

  return router;
}

module.exports = { createExamplesRouter };
