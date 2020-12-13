# Charge Scheduling

## What's changing?

In v1.2.1, we (finally) introduce a new Charge Scheduling UI, and with it a few new Charge Scheduling features.

Unfortunately, these features are not directly backwards compatible. For this reason, the approach involves taking 3 key steps towards a migration to the new scheduling functions:

   * Step 1: Introduce UI and gather feedback, with previous functionality level available

      * In this stage, features such as setting Charge Times per Day, and scheduling charges down to the minute are exposed in the new UI and can be configured, but will be written in a backwards-compatible format as well as a new format, with only the current level of Charge Scheduling support (single schedule across multiple days) being implemented.

      * This allows configuration of Charge Schedule using the new Web UI, but also allows us to structure the new UI in a way that takes advantage of new features. It will still be compatible with the old Web UI, and allows configuration of scheduling with a partial feature set from the new Web UI.

   * Step 2: Migration of existing Charge Schedule settings to new configuration structure

      * Step 2 will occur sometime after the initial Step 1 implementation, but will only occur in instances where the new UI has not been used - existing deployments. This will migrate current settings to the new structure on a once-off basis

   * Step 3: Deprecation of old interface

      * Step 3 involves the Charge Policy code being switched from the old configuration parameters to the new configuration parameters, and the enabling of new functionality. At this point, the legacy Web UI will no longer be capable of configuring Charge Scheduling.

