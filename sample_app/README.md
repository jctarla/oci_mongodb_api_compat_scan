# sample_app

Sample Node.js application for validating the OCI Mongo API compatibility scanner.

## Purpose

This project intentionally uses incompatible MongoDB items so the scanner can detect them during validation. It includes examples of unsupported query operators, update operators, aggregation stages, aggregation expressions, commands, and BSON types.

Scanner script:

- `../mongo_oci_compat_scan.py`

## Structure

- `src/app.js`: Express API and MongoDB connection setup
- `src/db/client.js`: MongoDB client lifecycle helper
- `src/services/incompatibleExamples.js`: intentionally incompatible MongoDB usage examples
- `src/routes/examples.js`: preview and execution endpoints

## Installation

```bash
cd sample_app
cp .env.example .env
npm install
npm start
```

## Endpoints

- `GET /health`
- `GET /examples/preview`
- `POST /examples/run`

## Validate with the Scanner

```bash
../mongo_oci_compat_scan.py \
  . \
  --output-json report.json
```

The report should include:

- incompatibilities grouped by file, item, and count
- MongoDB driver validation, including references such as `mongodb` and `mongoose`

## Notes

The examples are intentionally unsafe for OCI Mongo API compatibility. This app is meant for scanner validation, not as a production application template.
