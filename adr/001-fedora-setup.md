# Fedora Setup

> [!TIP]
> This is a brief ADR but can be extended as we make further decisions on how to setup/manage Fedora

## Background

[RFC 001](../rfcs/001-what-is-stored-in-fedora.md) outlines _what_ we store in Fedora. This document outlines how we plan to manage and configure Fedora.

The general principal is to keep the setup as _standard_ as possible, in keeping with "Fedora as a means to OCFL".  We will try to avoid customisations or bespoke elements to Fedora.

## Dockerfile

We will run Fedora as a Docker container, using the [official Fedora Docker image](https://github.com/fcrepo-exts/fcrepo-docker/), which runs Fedora via Tomcat. Fedora mentions both Jetty and Tomcat in docs but sticking with the official image removes this decision and should keep us consistent with other users. Any changes to hosting environment would require changes but trade-off of it being the official approach outweighs any risk.

## Configuration

We will use the following configuration:

* OCFL Storage Root will be on [S3](https://wiki.lyrasis.org/display/FEDORA6x/Amazon+S3)
* PostgreSQL database will be used for OCFL cache
* Digest algorithm use by OCFL will be sha256
* OCFL extension [Hashed N-tuple Storage Layout](https://ocfl.github.io/extensions/0004-hashed-n-tuple-storage-layout.html) will be used with default values.

## Customisation

Fedora [properties](https://wiki.lyrasis.org/display/FEDORA6x/Properties) can be customised by specifying `-D` command-line arguments or via a Java properties file on the host environment. There are other extensibility points, such as [logging](https://wiki.lyrasis.org/display/FEDORA6x/Logging) or [Tomcat-users](https://wiki.lyrasis.org/display/FEDORA6x/Servlet+Container+Authentication+Configuration#ServletContainerAuthenticationConfiguration-Tomcat), that operate by having an existing file on disk and directing Fedora to it.

As we're running in a containerised environment, rather than customising the host or making changes to the official Dockerfile we have chosen to use a custom sidecar container to bootstrap the host environment on startup (see [image readme.md](https://github.com/uol-dlip/preservation-ops/blob/main/images/fedora/bootstrap/readme.md)). As documented in linked readme this will allow us to securely pull in secrets etc.

## Hosting

Fedora will be hosted in AWS ECS. The compute and scaling configurations will need to be identified as we approach production environment as it will be driven by usage, file size etc.

We will start small and scale as required. We will need to load-test prior to production to get an accurate idea of required resources.

### Future / Production Improvements

The following are some areas we may want to investigate as we approach production environment:

* Hook into the [JMS messaging system](https://wiki.lyrasis.org/display/FEDORA6x/Messaging) to get audit events. We could use Amazon MQ, which is a managed Apache ActiveMQ service, as it supports STOMP and openwire protocols. However, this isn't as simple to setup as SQS as it involves provisioning compute resources to run brokers.
* Consume [Prometheus metrics](https://wiki.lyrasis.org/display/FEDORA6x/Metrics) from Fedora, again AWS have a managed service for this should we need it. Could be handy for figuring out scaling and performance.
* Scaling. Vertical scaling seems to be the common approach for Fedora. If horizontal scaling we could investigate sticky sessions or single write/multi read nodes. See [Fedora Slack](https://fedora-project.slack.com/archives/C8B5TSR4J/p1725379974486389) discussion related to this.