# PostgreSQL

PostgreSQL is an amazing RDBMS (Relational Database Management System). It has super easy backup tools, and generally is easy to manage.

## Installation

We are installing PostgreSQL in a Debian 13 LXC container. The installation is simple, and we can just use the official Debian repositories.

```shell
apt update
apt install postgresql -y
```

That should install everything you need to get up and running including the systemd files.

## Configuration

We are going to be using PostgreSQL numerous applications in our homelab. So we need to make sure that we set up strong ACL's within Postgres so that none of the applications can read other databases.

Postgres is already setup by default so that other users can not read inside the tables of another database, but they can view all the table names by default. We are going to set up our databases so that this is not possible.

We are also going to make it so that only the specific IP addresses for each application can access its database remotely. This is so that Nextcloud cannot access Paperless's database even if they had the paperless's username and password for that DB.

So in summary:

- Create a database and remove access for other users to read its table names.
- Restrict by IP each database so that they can only access their specific database.

### Creating a Database

First we are going to set the defacto standard for PostgreSQL. Edit the `/etc/postgresql/<version>/main/postgresql.conf` file so that it defaults to scram-sha-256.

```conf
password_encryption = scram-sha-256
```

Get into the shell for your PostgreSQL instance. You can't do this with root as by default in Postgres there is only the `postgres` user and no root.

```shell
runuser -u postgres -- psql
```

This will open up the Postgres shell as the `postgres` user, and we can now start to create our user, database and lockdown the database from other users.

```sql
CREATE USER username WITH PASSWORD 'super-good-password';
CREATE DATABASE database WITH OWNER username;
REVOKE ALL ON database FROM PUBLIC;
```

Now we have a database called `database` and it is owned by the user `username`.

You can run the command `\l+` to list out the databases that are currently in the RDBMS instance.

### Restricting IP's To Databases

By default, we aren't going to be able to connect to PostgreSQL without adding the application to the allow list of containers.

We can do this relatively simple with the `pg_hba.conf` file which is our host-based authentication file.

To add an entry, we can follow this structure.

| TYPE | DATABASE | USER | ADDRESS | METHOD |
|------|----------|------|---------|--------|
| host | database | username | 2001:db8::face/128 | scram-sha-256 |

Here is what your `pg_hba.conf` file could look like with your additions.

```conf
host minifluxdb minifluxuser 2001:db8::1 scram-sha-256
host giteadb giteauser 2001:db8::2 scram-sha-256
host nextclouddb nextclouduser 2001:db8::3 scram-sha-256
host paperlessdb paperlessuser 2001:db8::4 scram-sha-256
host autheliadb autheliauser 2001:db8::5 scram-sha-256
```

Just restart Postgres now to apply your changes.

```shell
systemctl restart postgresql
```
