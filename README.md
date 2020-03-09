# Smaland - Avanza API python wrapper

This is an unofficial python wrapper for the Avanza API. I am in no way affiliated with Avanza, using Smaland may violate the Avanza [terms of service](https://www.avanza.se/sakerhet-villkor/anvandarvillkor.html). 

## Installation 

Install via [pip](https://pypi.org/project/smaland/)
```bash
$ pip install smaland
```

## TOTP Secret

To log in through Smaland to Avanza, you need the TOTP Secret and log in with 2FA. To get the secret:

0. Go to Mina Sidor > Profil > Sajtinställningar > Tvåfaktorsinloggning and click "Återaktivera". (*Only do this step if you have already set up two-factor auth.*)
1. Click "Aktivera" on the next screen.
2. Select "Annan app för tvåfaktorsinloggning".
3. Click "Kan du inte scanna QR-koden?" to reveal your TOTP Secret.
5. Save the 2FA secret in a safe place, preferably a password manager. 
6. Temporarly save you avanza username, password, and secrit to a .env file (and add the .env file to your .gitignore)

```.env
username_av=my_username
password_av=my_password
secret_av=my_secret
```

7. When logging into Avanza through Smaland, enter the credentials as: 

```python
from smaland import Smaland
import dotenv
import os

#Load environment variables 
dotenv.load_dotenv()

credentials = {
    "username" : os.getenv("username_av"),
    "password" : os.getenv("password_av"),
    "secret" : os.getenv("secret_av")
}

sl = Smaland()
sl.authenticate(credentials)
```

## LICENSE

MIT license. See the LICENSE file for details.

## RESPONSIBILITIES

The author of this software is not responsible for any indirect damages (foreseeable or unforeseeable), such as, if necessary, loss or alteration of or fraudulent access to data, accidental transmission of viruses or of any other harmful element, loss of profits or opportunities, the cost of replacement goods and services or the attitude and behavior of a third party.


## Acknowledgment

This wrapper was inspired by the node [Avanza-api](https://github.com/fhqvst/avanza), where the author did a great job in finding all the endpoints etc. Thank you!
