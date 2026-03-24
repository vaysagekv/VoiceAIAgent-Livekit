# Twilio Integration with LiveKit

This document describes how to integrate Twilio programmable voice with LiveKit to accept inbound calls and route them to LiveKit rooms.

## Prerequisites

- A Twilio account with a purchased phone number
- LiveKit CLI installed and configured
- A LiveKit Cloud project or self-hosted LiveKit server

## Overview

To accept inbound calls using Twilio programmable voice, you need:
1. An inbound trunk created using LiveKit CLI (or SDK)
2. A dispatch rule to route callers to LiveKit rooms

> **Note:** This method doesn't support SIP REFER or outbound calls. To use these features, switch to Elastic SIP Trunking. For details, see the [Configuring Twilio SIP trunks quickstart](https://docs.livekit.io/sip/quickstarts/configuring-twilio-trunk/).

---

## Step 1: Purchase a Phone Number from Twilio

If you don't already have a phone number, follow Twilio's guide: [How to Search for and Buy a Twilio Phone Number From Console](https://www.twilio.com/docs/phone-numbers/quickstart).

---

## Step 2: Set up a TwiML Bin

TwiML Bins are a simple way to test TwiML responses. Use a TwiML Bin to redirect an inbound call to LiveKit.

> **Alternative approaches:** You can also return TwiML via another mechanism, such as a webhook.

### Create a TwiML Bin

1. Navigate to your [TwiML Bins page](https://www.twilio.com/console/twiml-bins)
2. Create a new TwiML Bin with the following contents:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Dial>
    <Sip username="<sip_trunk_username>" password="<sip_trunk_password>">
      sip:<your_phone_number_puchased_from_twilio>@<your LiveKit SIP endpoint>;transport=tcp
    </Sip>
  </Dial>
</Response>
```

---

## Step 3: Direct Phone Number to the TwiML Bin

Configure incoming calls to use the TwiML Bin you created:

1. Navigate to the [Manage numbers page](https://www.twilio.com/console/phone-numbers/incoming) and select the purchased phone number
2. In the **Voice Configuration** section, edit the "A call comes in" fields
3. Select **TwiML Bin** and choose the TwiML Bin created in the previous step

---

## Step 4: Create a LiveKit Inbound Trunk

Use the LiveKit CLI to create an inbound trunk for the purchased phone number.

### Create `inbound-trunk.json`

```json
{
  "trunk": {
    "name": "My inbound trunk",
    "numbers": ["<your_phone_number>"],
    "authUsername": "<sip_trunk_username>",
    "authPassword": "<sip_trunk_password>"
  }
}
```

> **Important:** Use the same phone number, username, and password that's specified in the TwiML Bin.

### Create the Inbound Trunk

```bash
lk sip inbound create inbound-trunk.json
```

---

## Step 5: Create a Dispatch Rule

Use the LiveKit CLI to create a dispatch rule that places each caller into individual rooms named with the `call-` prefix.

### Create `dispatch-rule.json`

```json
{
  "sipDispatchRuleId": "SDR_NpPUkHdMVB8A",
  "rule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "call-"
    }
  },
  "trunkIds": [
    "ST_4aAkTTS3ZfzU"
  ],
  "name": "Call Attending Agent Dispatch",
  "roomConfig": {
    "agents": [
      {
        "agentName": "call-attending-agent",
        "metadata": "{\"call_type\": \"inbound_after_hours\"}"
      }
    ]
  }
}
```

### Create the Dispatch Rule

```bash
lk sip dispatch create dispatch-rule.json
```

### Matching a Specific Trunk

If you already have a default caller dispatch rule and want to match a specific trunk, use the `--trunks` flag with the ID of the trunk you created:

```bash
lk sip dispatch create dispatch-rule.json --trunks "<trunk-id>"
```

---

## Testing with an Agent

1. Follow the [Voice AI quickstart](https://docs.livekit.io/agents/quickstart/) to create an agent that responds to incoming calls
2. Call the phone number - your agent should pick up the call

---

## Related Resources

- [LiveKit Agents Quickstart](https://docs.livekit.io/agents/quickstart/)
- [Configuring Twilio SIP Trunks](https://docs.livekit.io/sip/quickstarts/configuring-twilio-trunk/)
- [Twilio Documentation](https://www.twilio.com/docs)