# Qrater

Qrater (_Quality Rater_) is a containerized [Flask](https://flask.palletsprojects.com/en/2.0.x/)
web-application that allows the rating of quality control (QC) images in the browser.
It is built in a way that allows to QC a large quantity of images in a quick an easy way.
Qrater has a built-in WSGI HTTP server that allow the simultaneous rating by multiple users;
while its integrated [MySQL database](https://dev.mysql.com/doc/) and [Redis backserver](https://redis.io/)
make it possible to load and store datasets of tens of thousands of images and breeze through them in the process of QC.

![RatingExample](../assets/ImprovedDemo.png?raw=true)
## Installation

Qrater can be installed on a personal computer for the local use of a single rater,
or in a server or centralized computer cluster to be accessible by a team of raters simultaneously.

### Pre set-up
#### Docker Compose
Qrater consists on a set of containers ([MySQL 8](https://hub.docker.com/_/mysql/),
and [Redis 6](https://hub.docker.com/_/redis/)) linked to the Flask application.
To easily run and manage the containers together, [Docker Compose](https://docs.docker.com/compose/) is needed.
Most Windows and Mac user have it already, as it is installed together with Docker Desktop.
For Linux users, its [separate installation](https://docs.docker.com/compose/install/) is required.

#### E-mail
For some Qrater functionalities it is necessary to set up an e-mail account that will be used by the application to send information/forms to its users (e.g. password restoration) and its administrator (logs and traceback when an error occurs).

You can use your own personal e-mail account or, if you feel uncomfortable inputting your own password, create a new one just for this purpose.

An e-mail from any service can be used for this by setting the appropriate information (i.e. Server address, Port, TLP, etc.) in the Qrater's environmental variables in `qrater.env`. The settings for a gmail account are pre-set up by default; if your account is from gmail you only need to input that account's username; [see below](#add-environment-variables)).

### Set-up

Whether you're setting up Qrater on a personal computer for local use (either by a single rater or by several at
different times on the same computer), on a computer cluster or a server that can be accessible by ssh,
follow the steps below on the computer that is going to host the application.

#### Clone the Repo
Clone this repository and enter the installed directory:

```
git clone https://github.com/soffiafdz/Qrater.git; cd Qrater
```

#### Create password files

Within the cloned repo, two files need to be created: the database and mail password text files.
For security reasons, these files are not included and should be unique for each installation.
Both of these are normal `.txt` files with specific names (`db-password.txt` and `mail-password.txt`).
The first one will contain the password used by the MySQL database and the second the password of the e-mail Qrater will use to send e-mails ([see above](#e-mail)):

```
# Create the db-password file with the desired password as its only first and only line:
echo AVerySecretPassword > db-password.txt

# Do the same with Qrater's e-mail password:
echo eMailAccountPassword > mail-password.txt

# OR, if you are not setting up an e-mail, create the file but leave it empty:
touch mail-password.txt
```

#### Add environment variables

There is already a file `qrater.env.template` with some preset environmental variables and others that need to be set up.
Add the following information:

- `SECRET_KEY`: a secret key or password (or any random series of characters/numbers) that will serve as a cryptographic key for generating signature and tokens.
- `ADMINS_MAIL`: your e-mail; the e-mail to which Qrater will send logs when an error occurs (to enable this functionality, an e-mail account must also be setup)
- `MAIL_USERNAME`: Qrater's e-mail; the e-mail account username (everything before the @) that Qrater will use to send logs and password restoration forms.

 Once the missing information is filled, save the changes, and delete the `.template` portion of the name:

```
mv qrater.env.template qrater.env
```

#### Run the containers

Once the password files have been created and the environmental variables set,
the containers can be launched with Docker Compose:

```
# This command must be run from within the container:
docker-compose up --detach
```

You can check that all of the containers are up and running with this command:

```
# Check containers status with Docker Compose
docker-compose ps
```


After this, Qrater will be running on port `8080` and ready to be accessed.

## Usage

### Local access

To access the application from the same computer that is running,
open your browser and put `localhost:8080` in the address bar.

[screencap]

### Remote access

Qrater is most useful when it is running on a centralized server or computer cluster that can be accessed by different
`CLIENT` machines at the same time.

#### SSH port forwarding

If you have remote access by ssh to the `HOST` machine that is running Qrater,
you can access it from a remote `CLIENT` by creating a tunnel between the machines.

##### Linux or Mac

Open a terminal and create the tunnel between a port in your machine (in this case `8080`)
to the port `8080` of `HOST` with the `-L` option of ssh:

```
ssh -L 8080:127.0.0.1:8080 user@host
```

##### Windows

###### Integrated OpenSSH

Although Windows did not use to have an integrated SSH client,
since 2015 Windows now has an integrated OpenSSH client.
If your windows installation is up to date, it should be already enabled.
If it is not,
[follow these instructions](https://www.howtogeek.com/336775/how-to-enable-and-use-windows-10s-built-in-ssh-commands/)
to enable it before proceeding.

Open a PowerShell window, (right-click the Start button, or press Windows + X and choose "Windows PowerShell"),
and create the tunnel between a port in your machine to the port `8080` of `HOST` with the `-L` option of ssh:

```
ssh -L 8080:127.0.0.1:8080 user@host
```

###### SSH client or remote desktop

If you can or don't want to use the integrated OpenSSH client,
you can also also create the tunnel with
[PuTTY](https://www.putty.org/) or
[MobaXterm](https://mobaxterm.mobatek.net/),
or remotely accessing the graphical desktop directly with
[X2GO](https://wiki.x2go.org/doku.php/doc:newtox2go).

After the tunnel has been established, you can now access Qrater with `localhost:8080` in the browser.

![LandingPage](../assets/ImprovedDemo.png?raw=true)
