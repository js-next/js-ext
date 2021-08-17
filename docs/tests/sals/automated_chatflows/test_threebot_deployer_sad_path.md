### test01_deploy_threebot_on_past_expiration

Test case for deploying a threebot with an expiration on the past.

**Test Scenario**

- Deploy a threebot with an expiration on the past.
- Check that threebot deploying has been failed.

### test02_deploy_two_threebot_with_same_name

Test case for deploying two threebot with same name.

**Test Scenario**

- Deploy a threebot.
- Try to deploy anther threebot with same name.
- Check that second threebot deploying has been failed.

### test03_change_location_of_running_threebot

Test case for changing the location of running threebot.

**Test Scenario**

- Deploy a threebot.
- Try to change location for runing threebot.
- Check that threebot changing location has been failed.

### test04_change_size_of_running_threebot

Test case for changing the size of running threebot.

**Test Scenario**

- Deploy a threebot.
- Try to change size for runing threebot.
- Check that threebot changing size has been failed.

### test05_start_running_threebot

Test case for start running threebot.

**Test Scenario**

- Deploy a threebot.
- Try to start runing threebot.
- Check that start threebot running has been failed.

### test06_threebot_expiration_time

Test case for checking threebot expiration time.

**Test Scenario**

- Deploy a threebot.
- Get the expiration value.
- Check expiration value after one hour.

### test07_ssh_threebot

Test case for ssh threebot.

**Test Scenario**

- Prepare ssh key.
- Deploy threebot with ssh key.
- Up wireguard.
- Check ssh to threebot.
