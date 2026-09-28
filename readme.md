# [zotero-slack-alert](https://github.com/juancarloscastillo/zotero-slack-alert)

This repo/template describes the implementation of a Zotero Slack alert system. It uses the Zotero API to check for new items in a specified library and sends a notification to a Slack channel via a webhook when new items are detected. The automation is set up as a GitHub Action workflow that runs on a schedule (e.g., every hour) to continuously monitor the Zotero library for updates. It works for a complete Zotero folder or a subfolder (collection).  

It assumes that:

- You have a Zotero account and access to a group/library that you want to monitor. I used this for a group library, but it should work for personal libraries as well.
- You have a Slack workspace and the necessary permissions to create a webhook for a channel.

## Gathering the pieces

To make it work you only need to **copy the repo** (easy via template button) and create a new one in your user or organization you have permission to. BUT ... in case you want to add this to an existing repo, follow the steps at the end.

First, get this information: 

1. A Zotero group/library ID to monitor for new items. Go to your Zotero web library and get the number in the web address, for example `https://www.zotero.org/groups/<group_id_number>/...`.
  - The number that appears after `groups` is the value for **`GROUP_ID`**.
  - Do not use the whole Zotero URL as the secret value.

2. A Zotero API key with access to the specified group/library: to create an API key, go to [your Zotero account settings, navigate to the "API Keys" section,](https://www.zotero.org/settings/security#applications) and generate a new key with the appropriate permissions for the group/library you want to monitor. IMPORTANT: select _Read access to groups_ and _Read access to items_. Copy the API code in a safe place. This is the **`ZOTERO_API_KEY`**.

3. A Slack webhook URL to send notifications to a Slack channel: install the "Incoming Webhooks" app in your Slack workspace. Go to [this link](https://datasoc-workspace.slack.com/marketplace/A0F7XDUAZ-incoming-webhooks), select the appropriate workspace (up right), then green button "Add to Slack", and in the configuration the important is to select the slack channel where to get the alerts and copy the URL of the webhook. This is the **`SLACK_WEBHOOK`**.

4. Optional features are described at the end of this README.

## Now the Secrets

Now you just need to set up these pieces of information as "Github Secrets" in the repository settings. This way, the GitHub Action workflow can access them securely when it runs. For this: 

- go to the repository on GitHub, click on "Settings" (top right), then "Secrets and variables" > "Actions" > new repository secret
- to set up the `GROUP_ID` secret, enter `GROUP_ID` as the name and paste the group/library ID you found in step 1 as the value in the textbox, then click "Add secret"
- the same for the other required values, so at the end you should have these three required secrets: `GROUP_ID`, `ZOTERO_API_KEY`, and `SLACK_WEBHOOK`.
  
![](images/secrets.png)

If you want to test it, you can trigger the workflow manually from the "Actions" tab in your GitHub repository. Just select the workflow and click on "Run workflow". You should see the workflow run and, if there are new items in the Zotero library, a notification should appear in your Slack channel.
That's it! 

## Optional feature: Monitor one folder/collection (with or without subcollections)

By default, this template monitors the whole group library.

If you prefer to monitor only one Zotero folder/collection:

1. Add a `COLLECTION_KEY` secret.
  - This is the code that appears after `collections` in the Zotero URL.
  - Example: in `.../collections/25QRNU6T/collection`, the key is `25QRNU6T`.

2. Choose whether to include nested subcollections:
  - Add `INCLUDE_SUBCOLLECTIONS=true` to include nested folders.
  - Use `INCLUDE_SUBCOLLECTIONS=false` (or leave it unset) to monitor only the selected folder.

AND, in case you prefer to **add the workflow to an already existing repo**, download the folder and copy it in the root of your repo. And two more hacks:
- move the .github/workflow folder into the root
- update the path to the script in the .github/workflow/zotero.yml file, line 32 to:  `run: python zotero-slack-alert-main/zotero_alert.py




