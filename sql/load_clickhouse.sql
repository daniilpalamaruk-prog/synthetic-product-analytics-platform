-- Set user_files_path or replace each absolute glob before execution.
INSERT INTO synthetic_saas.users SELECT * FROM file('/path/to/data/clean/users/*.parquet', Parquet);
INSERT INTO synthetic_saas.sessions SELECT * FROM file('/path/to/data/clean/sessions/*.parquet', Parquet);
INSERT INTO synthetic_saas.events SELECT * FROM file('/path/to/data/clean/events/*.parquet', Parquet);
INSERT INTO synthetic_saas.subscriptions SELECT * FROM file('/path/to/data/clean/subscriptions/*.parquet', Parquet);
INSERT INTO synthetic_saas.payments SELECT * FROM file('/path/to/data/clean/payments/*.parquet', Parquet);
INSERT INTO synthetic_saas.marketing_spend SELECT * FROM file('/path/to/data/clean/marketing_spend/*.parquet', Parquet);
INSERT INTO synthetic_saas.fx_rates SELECT * FROM file('/path/to/data/clean/fx_rates/*.parquet', Parquet);
INSERT INTO synthetic_saas.experiments SELECT * FROM file('/path/to/data/clean/experiments/*.parquet', Parquet);
INSERT INTO synthetic_saas.experiment_assignments SELECT * FROM file('/path/to/data/clean/experiment_assignments/*.parquet', Parquet);
INSERT INTO synthetic_saas.feature_catalog SELECT * FROM file('/path/to/data/clean/feature_catalog/*.parquet', Parquet);
INSERT INTO synthetic_saas.app_releases SELECT * FROM file('/path/to/data/clean/app_releases/*.parquet', Parquet);
INSERT INTO synthetic_saas.generator_config SELECT * FROM file('/path/to/data/clean/generator_config/*.parquet', Parquet);
INSERT INTO synthetic_saas.business_timeline SELECT * FROM file('/path/to/data/clean/business_timeline/*.parquet', Parquet);
INSERT INTO synthetic_saas.pipeline_runs SELECT * FROM file('/path/to/data/clean/pipeline_runs/*.parquet', Parquet);
