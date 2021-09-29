# Tesla API DNS Redirection Trick

## Introduction

In September 2021, Tesla (once again) changed the API login flow. In the past, we've adopted the Tesla login flow, however this time they added an element to the flow that prohibits us from doing this.

They have added an origin check to the login flow. This origin check has the effect of requiring that the Capcha Check be run from a tesla.com domain.

## Workaround

To work around this requirement, you need to make a change on your side (or use a different method). 

The change involves a DNS host file entry (or appropriate entry on your router or DNS resolver if you're able) which points a subdomain of tesla.com, such as twcmanager.tesla.com at your TWCManager instance.

If you do this, and access TWCManager with this URL (eg http://twcmanager.tesla.com:8080), you will be able to log in using your Tesla credentials and completing a Recaptcha challenge. If your setup is compatible, you'll see a Congratulations message and see the Captcha prompt.

### Hosts file entry

The hosts fie entry should look like this:

```
192.168.1.1	twcmanager.tesla.com
```

The hosts file is located at ```c:\windows\system32\drivers\etc\hosts```
