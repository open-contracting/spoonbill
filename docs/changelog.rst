Changelog
=========

.. Follow the format from https://keepachangelog.com/en/1.0.0/

1.0.9b9 (2021-10-15)
--------------------
Fixed
~~~~~
* Fixed tool raising exception with UK tender data (`194638 <https://github.com/open-contracting/spoonbill/commit/194638248aed484f1a93fd6a4589f54d62563b6d>`__)


1.0.9b8 (2021-09-22)
--------------------
Fixed
~~~~~
* Headers for splitted child table (`2c97e6f <https://github.com/open-contracting/spoonbill/commit/2c97e6fc8b3c4a2827186cfd9faa2bb61d66fdf8>`__)


1.0.8b8 (2021-09-20)
--------------------
Fixed
~~~~~
* Empty columns after split of child table (`0ec4e97 <https://github.com/open-contracting/spoonbill/commit/0ec4e97ac5568087512c238612254a09182f3a62>`__)


1.0.7b8 (2021-09-20)
--------------------
Changed
~~~~~~~
* new analyzer engine (`58c4673 <https://github.com/open-contracting/spoonbill/commit/58c4673637624217a587911a83f83accb6430be9>`__)

Fixed
~~~~~
* fix pretty title generation for count columns (`637b876 <https://github.com/open-contracting/spoonbill/commit/637b87681382e0e91c22059cd9b4d51896d481e9>`__)
* **cli** fixed dump analyzed data to state file (`608f03d <https://github.com/open-contracting/spoonbill/commit/608f03d592373843eab336051675e9ff858ac86e>`__)
* **flatten** fixed splitting behavior (`0514883 <https://github.com/open-contracting/spoonbill/commit/0514883716694afa880187c8c83c339953682f22>`__)

1.0.7b7 (2021-09-10)
--------------------
Fixed
~~~~~
* additional formatting of human readable titles (`538592c <https://github.com/open-contracting/spoonbill/commit/538592c46976ebb62e0fdc2fd8a0fbd55b75d190>`__)

1.0.6b7 (2021-09-09)
--------------------
Added
~~~~~
* human readable titles are extracted from schema (`09f6f8a <https://github.com/open-contracting/spoonbill/commit/09f6f8a4c0c2e809bc2e4e6e28385c6f0f2c2ae4>`__)

1.0.6b6 (2021-07-14)
--------------------
Fixed
~~~~~
*  combined table's extensions are missing from export (`b1e897b <https://github.com/open-contracting/spoonbill/commit/b1e897bb87365cb8495aa57b6958f14292883780>`__)
*  table's extensions are missing from export (`6ebd662 <https://github.com/open-contracting/spoonbill/commit/6ebd6621d27b6dfccd39d497a6f7fdb3c366bb25>`__)
*  `JsongrefError` for record schema (`b2d6066 <https://github.com/open-contracting/spoonbill/commit/b2d606626f0368d86094073ce21d982b4e89a76a>`__)
*  locale is set to EN if it's absent (`b5d2aa9 <https://github.com/open-contracting/spoonbill/commit/b5d2aa9dd95708bbea6180986d6b57cdf0327bbf>`__)

1.0.5b6 (2021-07-14)
--------------------
Added
~~~~~
*  ordering tables according to schema  (`894d399 <https://github.com/open-contracting/spoonbill/commit/894d399bda27d8b7cbee718e42026cb2b962a91e>`__)

1.0.5b5 (2021-06-24)
--------------------
Added
~~~~~
*  multiple file input support  (`225c570 <https://github.com/mariob0y/spoonbill/commit/225c570ade34f02dddedcf85344d80f97a7ee449>`__)

1.0.5b4 (2021-06-18)
--------------------
Fixed
~~~~~

*  `.gz` format recognition enhancement (`9283ba4 <https://github.com/open-contracting/spoonbill/commit/9283ba451008b5542a73feceb7e4189d47862bcb>`__)


1.0.4b4 (2021-06-17)
--------------------
Added
~~~~~

*  added `.gz` support (`ed60751 <https://github.com/open-contracting/spoonbill/commit/d226a240549c97d8ea64f774c074e434114c026f>`__)

1.0.4b3 (2021-06-15)
--------------------

Fixed
~~~~~
*   pass `multiple_values` via `DataPreprocessor` (`509a06d <https://github.com/open-contracting/spoonbill/commit/509a06de79ca32d04e83b101a9eb55019b7c3d88>`__)

1.0.3b3 (2021-06-15)
--------------------

Added
~~~~~

*  added jsonl support (`59ec81c <https://github.com/open-contracting/spoonbill/commit/59ec81c1742daca043c233a29b7aeb48c9934b98>`__)

Fixed
~~~~~

*  fix `FileFlattener` input (`acacd87 <https://github.com/open-contracting/spoonbill/commit/acacd870409fe5bdd88e1f0c10f12bc915983167>`__)


1.0.3b2 (2021-06-07)
--------------------

Added
~~~~~

*  add Row and Rows containers to keep rows data and their relations
   (`4e8a385 <https://github.com/open-contracting/spoonbill/commit/4e8a3857c8767f5f74ba7a614782c921563b34b7>`__)

Fixed
~~~~~

*  **cli:** fixed variable shadowing in a loop (`1a55141 <https://github.com/open-contracting/spoonbill/commit/1a5514104086259a4c57ca33866dcb2f7822bcb6>`__)
*  fix parentTable generation for combined tables (`5e06bf0 <https://github.com/open-contracting/spoonbill/commit/5e06bf09088307b94afa26e223a9aae8d10df12a>`__)
*  parentID should be rowID for parent table (`c429309 <https://github.com/open-contracting/spoonbill/commit/c429309d3b265fdb2d7fb632e83bb7d2a373b7fc>`__)
*  .xlsx writer ``only`` error handling (`ebc2ad0 <https://github.com/open-contracting/spoonbill/commit/ebc2ad0456e33ba8d81eacee51fec0974640e0ba>`__)
*  **setup:** add include_package_data to setup.py (`db8b63b <https://github.com/open-contracting/spoonbill/commit/db8b63b3150166e5589d9dbd675547a3f709436c>`__)

1.0.2b1 (2021-06-02)
--------------------

Fixed
~~~~~

* **analyze:** recalculate headers recursively (`ca1c521 <https://github.com/open-contracting/spoonbill/commit/ca1c521c74b638b427d40f43f7d0575238a57d1d>`__)
* **stats:** pregenerate headers for exstention table when detected (`648485c <https://github.com/open-contracting/spoonbill/commit/648485c7539ba4c0c0af220587d347aaebba9aca>`__)
* **stats:** fix inserting array columns into rolled up table columns (`d6d6195 <https://github.com/open-contracting/spoonbill/commit/d6d61951430bd2c049765e826957d3ae56c8cd20>`__)
* Use correct type annotation for List (`9d16a3f <https://github.com/open-contracting/spoonbill/commit/9d16a3f26309cff54c31ac27adfd49e41ac09801>`__)

1.0.1b1 (2021-05-27)
--------------------

Fixed
~~~~~

* **flatten:** strict columns match in only option

1.0.0b1 (2021-05-26)
--------------------

Added
~~~~~

* **cli:** add --unnest-file, --repeat-file and --only-file options (`9b024e2 <https://github.com/open-contracting/spoonbill/commit/9b024e2ae93d22d9a9a33b2f5b74edc1039c604d>`_)
* **cli:** add click integration with logging (`3c1184f <https://github.com/open-contracting/spoonbill/commit/3c1184f9d05f669401b30a2d7350126b631bbaf5>`_)
* **cli:** add informational messages about only, unnest and repeat (`2e6d48e <https://github.com/open-contracting/spoonbill/commit/2e6d48e09345669a743c436e2c4bdc85fc7f5dbb>`_)
* **cli:** add language option (`1d89e0b <https://github.com/open-contracting/spoonbill/commit/1d89e0b7d755cf7dc001e2aa65cb0a9ae22c1142>`_)
* **cli:** add progressbar when analyze file (`49e4440 <https://github.com/open-contracting/spoonbill/commit/49e44406d2c18c08e4bcbeeec5554fc6623acf7d>`_)
* **cli:** enable only and repeat options (`8b82f9e <https://github.com/open-contracting/spoonbill/commit/8b82f9eb42562e8291864fcd4f79234ef5938998>`_)
* **cli:** use click.progressabr in heavy operations (`1e27a09 <https://github.com/open-contracting/spoonbill/commit/1e27a096ffcbc94e9695ed700e9091a5de166c30>`_)
* **cli:** use csv and xlsx options to provide output paths (`bf8689d <https://github.com/open-contracting/spoonbill/commit/bf8689d6e6b3ee340db2a4a432fe7ec08e0163f4>`_)
* **csv:** more exception handling in csv writer (`9e85095 <https://github.com/open-contracting/spoonbill/commit/9e85095b9d8e680043bae4b1e4b181146a0daa2d>`_)
* **flatten:** add exclude option to remove table from export (`26025dd <https://github.com/open-contracting/spoonbill/commit/26025dd611b6512e8b0b1dabcb65cff0773b6417>`_)
* **flatten:** implement only option to specify list of output cols (`a57200b <https://github.com/open-contracting/spoonbill/commit/a57200bce0cb3ae51d05a8955ce9998470a26ddc>`_)
* **i18n:** add custom babel extractor to produce schema paths (`f602a69 <https://github.com/open-contracting/spoonbill/commit/f602a6968779be23e59c179beacf569ac0e2b79c>`_)
* **i18n:** add locale override option when using gettext (`638b9a8 <https://github.com/open-contracting/spoonbill/commit/638b9a8f3b35dcb4fd1cf18edc1f754c8ca761d7>`_)
* **i18n:** use localization mechanism as tool to generate h/r titles (`5e20df3 <https://github.com/open-contracting/spoonbill/commit/5e20df398a18980ec62ad700ce9aecac7f0ac15d>`_)
* add ability to rename sheet (`9d4c68d <https://github.com/open-contracting/spoonbill/commit/9d4c68df2340bdc631a062d976c215dd724a88ba>`_)
* add DataPreprocessor restore method to init from existing data (`1c3ada7 <https://github.com/open-contracting/spoonbill/commit/1c3ada7375717d7ab14eeb705a6545d1bc241315>`_)
* implement --state-file option to restore analyzer state from file (`a8294ea <https://github.com/open-contracting/spoonbill/commit/a8294ea292989a6528c76fdde462ed88346e2e5b>`_)
* make DataPreprocessor.process_items iterable to track progress (`380196f <https://github.com/open-contracting/spoonbill/commit/380196ff3bcb70fd4b901df834abcf8d12024239>`_)
* table threshold option now enabled by default (`42283e6 <https://github.com/open-contracting/spoonbill/commit/42283e6e283335f5d5f8940c825aa2486b45ff24>`_)

Changed
~~~~~~~

* Add lru_cache for common_prefix, and compare len() instead of using min() and max() (`694135c <https://github.com/open-contracting/spoonbill/commit/694135ce220b565dd9a19fbf1470224f485c79b0>`_)
* Use pickle instead of json (`63a4265 <https://github.com/open-contracting/spoonbill/commit/63a42653f95d9a9a134ef560c863351b84643f20>`_)

Fixed
~~~~~

* **cli:** drop --split option and introduce --exclude (`35f1391 <https://github.com/open-contracting/spoonbill/commit/35f13911c770ed7ef76d612d23f30e7063122a2a>`_)
* use pkg_resources.resource_filename to access locales (`be48d77 <https://github.com/open-contracting/spoonbill/commit/be48d7785c95a741771c3001ebc42a4eb067a966>`_)
* **stats:** fix IndexError when generating preview_rows for extra tables (`82b179b <https://github.com/open-contracting/spoonbill/commit/82b179b994d570eea3b08e99467105748812a1e8>`_)
* **utils:** make resolve_file_uri understand pathlib.Path (`51e82a3 <https://github.com/open-contracting/spoonbill/commit/51e82a3633837b5104ecfb4db604d69d619c948b>`_)
* use pickle instead of json in DataPreprocessor dump (`d0c516b <https://github.com/open-contracting/spoonbill/commit/d0c516bf194d72ac08a84cb0bf5a13f815b3c843>`_)
* **writers:** make writers context managers (`18e4c09 <https://github.com/open-contracting/spoonbill/commit/18e4c097a01f95bbacda41cac00552608322463f>`_)
* add more logging messages (`9205217 <https://github.com/open-contracting/spoonbill/commit/920521716cd4532f9649b1651ad108c742bec04a>`_)
* added logger filter for repetative messages (`f936d50 <https://github.com/open-contracting/spoonbill/commit/f936d5078abb37caf29ae7436c98333c0637fd7f>`_)
* added table abbreviation support (`85f46f3 <https://github.com/open-contracting/spoonbill/commit/85f46f3fcecf08b499728b2551fa3f63906a7805>`_)
* CLI export message edit - removed extra tables from message, added list of exported tables and number of rows for each (`9681c71 <https://github.com/open-contracting/spoonbill/commit/9681c7109d483114a95312ee0428c2e550a7249c>`_)
* CLI index out of range error, issue `#66 <https://github.com/open-contracting/spoonbill/issues/66>`_ (`0318558 <https://github.com/open-contracting/spoonbill/commit/03185587b1d17a7c638d8b1399d3208a56ec7491>`_)
* code refactor; added duplicate check to stats/DataPreprocessor (`fcfb611 <https://github.com/open-contracting/spoonbill/commit/fcfb6116050d62b0b5ea9474ac94b8834d34bea7>`_)
* fix crash with additional array of strings present in data (`4e73c70 <https://github.com/open-contracting/spoonbill/commit/4e73c70acbd75136c7ff317a574636c259fa5d88>`_)
* fix KeyError with adding count column in child tables (`36d5ccc <https://github.com/open-contracting/spoonbill/commit/36d5ccc109eefb0f12346674cfba1379616efc3a>`_)
* fixed bug with regenerated headers when array is shorter than table_threshold (`3e87b4c <https://github.com/open-contracting/spoonbill/commit/3e87b4ce6b9e15dd79db41ff053e33088f4356dc>`_)
* fixed KeyError when flattening data with additional arrays (`c7e3cd0 <https://github.com/open-contracting/spoonbill/commit/c7e3cd0f72b394571161c957ffa4ded63cd41ec0>`_)
* increment default columns when incrementing table rows (`3c602a6 <https://github.com/open-contracting/spoonbill/commit/3c602a641ea36a88e6a1787837b4e325b8cf65b0>`_)
* make name '_' explicit imported (`99932e0 <https://github.com/open-contracting/spoonbill/commit/99932e07637bf8d30d9bddcc6015b635cb83d18a>`_)
* strip lines when reading option file (`e57031b <https://github.com/open-contracting/spoonbill/commit/e57031b6897c082ee5daa7c12785d29a9bdd538c>`_)
* use OrderedDict as map container in iter_file (`0d1df1b <https://github.com/open-contracting/spoonbill/commit/0d1df1b14b4520cd416a98efadb4aca5e848f0f1>`_)
* writing booleans to .xlsx cells (`1d8de32 <https://github.com/open-contracting/spoonbill/commit/1d8de320278517a418ac989bc0c2fdb1879188bf>`_)
* **cli:** enable --threshold option (`852ff92 <https://github.com/open-contracting/spoonbill/commit/852ff92c156e4c904caec241d41d7d8aa9e1002e>`_)
* **cli:** fix variable naming (`c17ca63 <https://github.com/open-contracting/spoonbill/commit/c17ca632bc5eae347a4d0129d564c5d674ad382f>`_)
* **flaten:** fixed typo JOINABLE -> JOINABLE_SEPARATOR (`1adc440 <https://github.com/open-contracting/spoonbill/commit/1adc440e950a4e4b19cbd2435f362831befa1b2f>`_)
* **flatten:** fix only option causing empty output (`c8447b0 <https://github.com/open-contracting/spoonbill/commit/c8447b015683f606a10e3c9270dcb84eea95bf95>`_)
* **flatten:** fix repeat spreading to unrelated tables (`2e16c30 <https://github.com/open-contracting/spoonbill/commit/2e16c309a53857916693ca2aef09ce4891729cee>`_)
* **i18n:** generate message for count columns (`a527f8d <https://github.com/open-contracting/spoonbill/commit/a527f8dc91f52be00ae8b681984a85798a36065c>`_)
* **setup:** do not use babel cmds in setup.py (`e449c37 <https://github.com/open-contracting/spoonbill/commit/e449c3705f234c2eadc66553348873c4223ac679>`_)
* fixed mixing preview_rows and preview_rows combined (`dd1dd19 <https://github.com/open-contracting/spoonbill/commit/dd1dd1977ba0e86a8d762f16fdd9ce2d5379aa78>`_)
* fixed serialization of total_items (`055ff65 <https://github.com/open-contracting/spoonbill/commit/055ff657588e58599aee71a6eb4fd5297eaf0267>`_)
* remove copy column by reference in recalculate headers (`22c63f8 <https://github.com/open-contracting/spoonbill/commit/22c63f84e308e16ca0a95059ce06a99ac0864af7>`_)
* **stats:** respect with_preview when appending new preview row (`cfd8663 <https://github.com/open-contracting/spoonbill/commit/cfd8663f03ff7565da836b465eba9ead780e6e84>`_)
