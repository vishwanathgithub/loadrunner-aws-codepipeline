# loadrunner-aws-codepipeline
Integrate load-runner enterprise execution with AWS codepipeline
Execute Terminal command 
src/run_test.py $NFT_USERNAME $MF_PASSWORD $DOMAIN_NAME $PROJECT_NAME $TEST_ID $TEST_INSTANCE_ID $LOG_LEVEL
$NFT_USERNAME - String -  sourced from aws parameter store
$MF_PASSWORD - String - soured from aws secret manager
$DOMAIN_NAME - String - sourced from aws parameter store
$PROJECT_NAME - String - sourced from aws parameter store
$TEST_ID - String - sourced from aws parameter store
$TEST_INSTANCE_ID - String - sourced from aws parameter store
$LOG_LEVEL - String - sourced from aws parameter store

Reference - https://admhelp.microfocus.com/lre/en/all/api_refs/Performance_Center_REST_API/Content/Welcome.htm
