/*
  Intentionally incompatible examples for OCI Mongo API scanner validation.
  This module simulates real workloads and includes unsupported operators,
  stages, commands, and BSON type usages.
*/

const UNSUPPORTED_QUERY_OPERATORS = [
  '$bitsAllClear', '$bitsAllSet', '$bitsAnyClear', '$bitsAnySet',
  '$comment', '$expr', '$jsonSchema', '$mod', '$natural', '$where'
];

const UNSUPPORTED_UPDATE_OPERATORS = [
  '$currentDate', '$mul', '$rename', '$setOnInsert'
];

const UNSUPPORTED_AGGREGATION_STAGES = [
  '$bucketAuto', '$changeStream', '$changeStreamSplitLargeEvent', '$collStats',
  '$currentOp', '$geoNear', '$graphLookup', '$indexStats', '$listLocalSessions',
  '$listSessions', '$planCacheStats', '$redact', '$search', '$searchMeta',
  '$setWindowFields', '$unionWith'
];

const UNSUPPORTED_AGGREGATION_EXPRESSIONS = [
  '$binarySize', '$bsonSize', '$dateAdd', '$dateDiff', '$dateSubtract',
  '$dateToParts', '$dateTrunc', '$derivative', '$documentNumber', '$expMovingAvg',
  '$getField', '$indexOfArray', '$integral', '$isArray', '$locf', '$ltrim', '$map',
  '$maxN', '$meta', '$minN', '$percentile', '$rank', '$regexFind', '$regexFindAll',
  '$regexMatch', '$replaceAll', '$replaceOne', '$rtrim', '$sampleRate', '$setField',
  '$shift', '$sortArray', '$strLenBytes', '$toDecimal', '$tsIncrement', '$tsSecond',
  '$unsetField'
];

const UNSUPPORTED_COMMANDS = [
  'abortTransaction', 'authenticate', 'balancerCollectionStatus', 'bulkWrite',
  'cloneCollectionAsCapped', 'commitTransaction', 'connPoolStats', 'convertToCapped',
  'count', 'dbHash', 'distinct', 'driverOIDTest', 'endSessions', 'features',
  'filemd5', 'findAndModify', 'findandmodify', 'geoSearch', 'getCmdLineOpts',
  'getLog', 'getShardMap', 'getShardVersion', 'getnonce', 'hostInfo', 'isSelf',
  'killAllSessions', 'killAllSessionsByPattern', 'killCursors', 'listCommands',
  'logRotate', 'mapreduce', 'mapReduce', 'profile', 'reIndex', 'renameCollection',
  'repairDatabase', 'saslContinue', 'saslStart', 'setFeatureCompatibilityVersion',
  'setParameter', 'shardCollection', 'testDeprecation', 'testVersions1And2',
  'testVersion2', 'whatsmyuri'
];

const UNSUPPORTED_BSON_TYPES = [
  'dbPointer', 'javascript', 'javascriptWithScope', 'maxKey', 'minKey', 'regex', 'undefined'
];

async function seedSampleData(collection) {
  await collection.deleteMany({});
  await collection.insertMany([
    {
      customerId: 'c1',
      orderTotal: 120.5,
      qty: 3,
      flags: 10,
      city: 'Sao Paulo',
      location: { type: 'Point', coordinates: [-46.6333, -23.5505] },
      email: 'ana@example.com',
      createdAt: new Date(),
      status: 'open'
    },
    {
      customerId: 'c2',
      orderTotal: 48.9,
      qty: 1,
      flags: 4,
      city: 'Rio de Janeiro',
      location: { type: 'Point', coordinates: [-43.1729, -22.9068] },
      email: 'bruno@example.com',
      createdAt: new Date(),
      status: 'closed'
    }
  ]);
}

function buildUnsupportedFindFilter() {
  return {
    flags: { $bitsAllSet: [1, 3], $bitsAnyClear: [0, 2], $mod: [2, 0] },
    score: { $bitsAllClear: [5], $bitsAnySet: [2] },
    $comment: 'scanner-demo',
    $expr: { $gt: ['$orderTotal', 50] },
    $jsonSchema: {
      bsonType: 'object',
      required: ['customerId', 'email', 'qty'],
      properties: {
        customerId: { bsonType: 'string' },
        email: { bsonType: 'string', pattern: '^.+@.+\\..+$' },
        qty: { bsonType: 'int' }
      }
    },
    $where: 'this.qty > 0',
    hint: { $natural: 1 }
  };
}

function buildUnsupportedUpdateDoc() {
  return {
    $currentDate: { updatedAt: true },
    $mul: { qty: 2 },
    $rename: { city: 'shippingCity' },
    $setOnInsert: { insertedBy: 'scanner-demo' }
  };
}

function buildUnsupportedPipeline() {
  return [
    {
      $geoNear: {
        near: { type: 'Point', coordinates: [-46.63, -23.55] },
        distanceField: 'distanceMeters',
        spherical: true,
        maxDistance: 5000
      }
    },
    { $search: { text: { query: 'open', path: 'status' } } },
    { $searchMeta: { text: { query: 'open', path: 'status' } } },
    { $bucketAuto: { groupBy: '$orderTotal', buckets: 3 } },
    { $changeStream: {} },
    { $changeStreamSplitLargeEvent: {} },
    { $collStats: { storageStats: {} } },
    { $currentOp: { allUsers: true } },
    { $graphLookup: { from: 'orders', startWith: '$customerId', connectFromField: 'customerId', connectToField: 'customerId', as: 'graph' } },
    { $indexStats: {} },
    { $listLocalSessions: {} },
    { $listSessions: {} },
    { $planCacheStats: {} },
    { $redact: '$$DESCEND' },
    { $setWindowFields: { partitionBy: '$customerId', sortBy: { createdAt: 1 }, output: { rollingTotal: { $sum: '$orderTotal', window: { documents: [-1, 0] } } } } },
    { $unionWith: { coll: 'archived_orders' } },
    {
      $project: {
        payloadBytes: { $binarySize: '$status' },
        docBytes: { $bsonSize: '$$ROOT' },
        dtAdd: { $dateAdd: { startDate: '$createdAt', unit: 'day', amount: 1 } },
        dtDiff: { $dateDiff: { startDate: '$createdAt', endDate: '$$NOW', unit: 'hour' } },
        dtSub: { $dateSubtract: { startDate: '$$NOW', unit: 'day', amount: 7 } },
        dtParts: { $dateToParts: { date: '$createdAt' } },
        dtTrunc: { $dateTrunc: { date: '$createdAt', unit: 'day' } },
        deriv: { $derivative: { input: '$orderTotal', unit: 'hour' } },
        docNum: { $documentNumber: {} },
        expAvg: { $expMovingAvg: { input: '$orderTotal', N: 3 } },
        dynamicField: { $getField: { field: 'status', input: '$$ROOT' } },
        idxArray: { $indexOfArray: [['a', 'b', 'c'], 'b'] },
        integral: { $integral: { input: '$orderTotal', unit: 'hour' } },
        isArrayCheck: { $isArray: '$tags' },
        locf: { $locf: '$orderTotal' },
        ltrim: { $ltrim: { input: '$status' } },
        map: { $map: { input: ['$qty', '$orderTotal'], as: 'n', in: '$$n' } },
        maxN: { $maxN: { n: 1, input: '$orderTotal' } },
        meta: { $meta: 'textScore' },
        minN: { $minN: { n: 1, input: '$orderTotal' } },
        percentile: { $percentile: { input: '$orderTotal', p: [0.5], method: 'approximate' } },
        rank: { $rank: {} },
        regexFind: { $regexFind: { input: '$email', regex: /@/ } },
        regexFindAll: { $regexFindAll: { input: '$email', regex: /[a-z]+/ } },
        regexMatch: { $regexMatch: { input: '$email', regex: /example/ } },
        replaceAll: { $replaceAll: { input: '$status', find: 'o', replacement: '0' } },
        replaceOne: { $replaceOne: { input: '$status', find: 'o', replacement: '0' } },
        rtrim: { $rtrim: { input: '$status' } },
        sampleRate: { $sampleRate: 0.5 },
        setField: { $setField: { field: 'newField', input: '$$ROOT', value: 1 } },
        shift: { $shift: { output: '$orderTotal', by: 1 } },
        sortArray: { $sortArray: { input: [3, 1, 2], sortBy: 1 } },
        strLenBytes: { $strLenBytes: '$status' },
        toDecimal: { $toDecimal: '$orderTotal' },
        tsIncrement: { $tsIncrement: '$createdAt' },
        tsSecond: { $tsSecond: '$createdAt' },
        unsetField: { $unsetField: { field: 'status', input: '$$ROOT' } }
      }
    }
  ];
}

function buildUnsupportedCommands() {
  return UNSUPPORTED_COMMANDS.map((cmd) => ({ [cmd]: 1 }));
}

function buildUnsupportedBsonTypeExamples() {
  return {
    queryByTypeDbPointer: { strangeField: { $type: 'dbPointer' } },
    queryByTypeJavascript: { strangeField: { $type: 'javascript' } },
    queryByTypeJavascriptScope: { strangeField: { $type: 'javascriptWithScope' } },
    queryByTypeMaxKey: { strangeField: { $type: 'maxKey' } },
    queryByTypeMinKey: { strangeField: { $type: 'minKey' } },
    queryByTypeRegex: { strangeField: { $type: 'regex' } },
    queryByTypeUndefined: { strangeField: { $type: 'undefined' } }
  };
}

async function runIncompatibleExamples(db, collection) {
  const result = {
    attempted: {
      query_operators: UNSUPPORTED_QUERY_OPERATORS,
      update_operators: UNSUPPORTED_UPDATE_OPERATORS,
      aggregation_stages: UNSUPPORTED_AGGREGATION_STAGES,
      aggregation_expressions: UNSUPPORTED_AGGREGATION_EXPRESSIONS,
      commands: UNSUPPORTED_COMMANDS,
      bson_types: UNSUPPORTED_BSON_TYPES
    },
    errors: []
  };

  await seedSampleData(collection);

  try {
    await collection.find(buildUnsupportedFindFilter()).toArray();
  } catch (err) {
    result.errors.push({ op: 'find_with_unsupported_query_ops', message: err.message });
  }

  try {
    await collection.updateOne({ customerId: 'c1' }, buildUnsupportedUpdateDoc(), { upsert: true });
  } catch (err) {
    result.errors.push({ op: 'update_with_unsupported_update_ops', message: err.message });
  }

  try {
    await collection.aggregate(buildUnsupportedPipeline()).toArray();
  } catch (err) {
    result.errors.push({ op: 'aggregate_with_unsupported_stages_and_expressions', message: err.message });
  }

  for (const cmdBody of buildUnsupportedCommands()) {
    try {
      await db.command(cmdBody);
    } catch (err) {
      result.errors.push({ op: `command_${Object.keys(cmdBody)[0]}`, message: err.message });
    }
  }

  // Keep explicit BSON type examples referenced in executable flow.
  result.bsonTypeExamples = buildUnsupportedBsonTypeExamples();
  return result;
}

module.exports = {
  runIncompatibleExamples,
  buildUnsupportedFindFilter,
  buildUnsupportedUpdateDoc,
  buildUnsupportedPipeline,
  buildUnsupportedCommands,
  buildUnsupportedBsonTypeExamples
};
