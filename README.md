# Qrater

Qrater (_Quality Rater_) is a containerized [Flask](https://flask.palletsprojects.com/en/2.0.x/) web-application that allows the rating of quality control (QC) images in the browser. It is built in a way that allows to QC a large quantity of images in a quick an easy way. 
Qrater has a built-in WSGI HTTP server that allow the simultaneous rating by multiple users; while its integrated [MySQL database]() and [Redis backserver](https://redis.io/) make it possible to load and store datasets of tens of thousands of images and breeze through them in the process of QC.

## Installation

Qrater can be installed on a personal computer for the local use of a single rater, or in a server or centerized computer cluster to be accessible by a team of raters simultaneously.

### Pre set-up
#### Docker Compose
Qrater consists on a set of containers ([MySQL 8](https://hub.docker.com/_/mysql/), and [Redis 6](https://hub.docker.com/_/redis/)) linked to the Flask application.
To easily run and manage the containers together, [Docker Compose](https://docs.docker.com/compose/) is needed. 
Most Windows and Mac user have it already, as it is installed together with Docker Desktop. 
For Linux users, its [separate installation](https://docs.docker.com/compose/install/) is required.

#### E-mail
For some Qrater functionalities it is necessary to set up an e-mail account that will be used by the application to send information/forms to its users (e.g. password restoration) and its administrator (logs and traceback when an error occurs). 

An e-mail from any service (e.g. gmail, outlook, yahoo, protonmail, etc.) can be used setting the appropriate information in the Qrater's environmental variables ([see below](#add-environment-variables)). 


### Local installation

The most basic use of Qrater is to install it on a personal computer and do the rating (by a single rater or by several at different times) locally.

#### Clone the Repo
Clone this repository to the PC and change to the installed directory: 
```
git clone https://github.com/soffiafdz/Qrater.git; cd Qrater
```

#### Create password files

Within, two files need to be created: the database and mail passwords. For security reasons, these files are not included and should be unique for each installation.

For the databaset password, create a text file named `db-password.txt` with your password inside:
```
echo AVerySecretPassword > db-password.txt
```

The second file is named `mail-password.txt` and it contains the password for the e-mail account from which Qrater sends e-mails to its users.
```
echo eMailPassword > mail-password.txt
```

While these e-mail functions are optional, this file must exist. If no e-mail account is being set-up, create the file and leave it empty:
```
touch mail-password.txt
```

#### Add environment variables
 
There is already a file `qrater.env.template` with some preset environmental variables and others that need to set up.
Add the following information: 

- `SECRET_KEY`: a secret key or password (or any random series of characters/numbers) that will serve as a cryptographic key for generating signature and tokens.
- `ADMINS_MAIL`: your e-mail; the e-mail to which Qrater will send logs when an error occurs (to enable this functionality, an e-mail account must also be setup)
- `MAIL_USERNAME`: Qrater's e-mail; the e-mail account that Qrater will use to send you logs and password restoration forms for raters.

 Once the missing information is filled, save and delete the `.template` portion of the name:
```
mv qrater.env.template qrater.env
```



For instructions to access the running Qrater instance of the NIST lab in BIC see `attach link here`. 
