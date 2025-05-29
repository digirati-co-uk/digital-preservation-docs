# Release Management

Release management for Preservation repository: https://github.com/uol-dlip/digital-preservation


## Background

The release management is quite simple and straight forward. There is one core branch called main and pull requests merged to main branch will go directly to the Dev environment. All other environments should be created via a tagged release. 


## Release to Development 
This will happen automatically on PR (pull request) or merged to main branch. Use `no-deploy` tag for pull requests to avoid the PR getting deployed to development environment. 

## Create a tag Release

Navigate to github release location on GitHub.com: https://github.com/uol-dlip/digital-preservation/releases


### Create Release with a new TAG

Create a release with a new tag as shown below.



### Deploy tagged release

There are TWO github workflows that you can generated a release for
 
 - Preservation:  https://github.com/uol-dlip/digital-preservation/actions/workflows/build.yml
 - IIF Builder: https://github.com/uol-dlip/digital-preservation/actions/workflows/build_iiifbuilder.yml

 Both have similar workflow so only one workflow will be shown as example.

 Run the workflow and select tag (or branch) and target environment.

![alt text](..\img\release-006\run-workflow.png)


Select and run and it will build and deploy code to each evironment.



## How it works

This is brief summary on how the code is deployed.

1. Code is pulled and built.
2. docker image is built.
3. Image is push to AWS Elastic Container Service (ECS).
4. The tag is renamed dependant on environment chosen. 
5. The target environment is restarted and will load new image.


## EOF