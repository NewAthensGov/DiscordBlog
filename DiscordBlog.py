from typing import Union
import discord
from discord import option
from discord.ext import commands
import requests
import datetime
import re
import os
import shutil
from github import Github
from urllib.parse import urlparse

# Hardcoded tokens and repository details
DISCORD_TOKEN = 'your_discord_bot_token'
GITHUB_TOKEN = 'your_github_token'
REPO_OWNER = 'your_github_username'
REPO_NAME = 'your_repo_name'
BRANCH = 'main'  # Change if your branch is different


# Initialize Bot and GitHub
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)
g = Github(GITHUB_TOKEN)
repo = g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.slash_command(name="news")
@option("title", description="Enter the title of the blog post")
@option("author", description="Enter the author of the blog post")
@option("text", description="Markdown text content of the blog post")
@option("header_image", description="URL of the header image")
@option("link", description="External url to be included in the blog post", required=False)
async def news(
    ctx: discord.ApplicationContext,
    title: str,
    author: str,
    text: str,
    header_image: str,
    link: str = ""
):
    # Get the current date and time in the required format
    current_datetime = datetime.datetime.utcnow().isoformat() + 'Z'
    current_datetime_formatted = current_datetime.replace(':', '-').replace('T', '-').replace('Z', '')
    dashed_title = re.sub(r'[^a-zA-Z0-9\-]', '-', title.replace(' ', '-'))

    # Create the file paths
    image_folder = f'public/post/{dashed_title}-{current_datetime_formatted}'.replace('\\', '/')
    parsed_url = urlparse(header_image)
    image_file_name = os.path.basename(parsed_url.path)
    image_path = os.path.join(image_folder, image_file_name).replace('\\', '/')
    featured_image_path = f'{image_path}'.replace('public/', '')

    # Download the header image if provided
    if header_image:
        if not download_image(header_image, image_path):
            await ctx.respond('Failed to download image.')
            return

    # Create the blog post content based on provided arguments
    if header_image:
        post_content = f"""---
title: '{title}'
date: '{current_datetime}'
author: '{author}'
draft: false
featured_image: '{featured_image_path}'
---
"""
    else:
        post_content = f"""---
title: '{title}'
date: '{current_datetime}'
author: '{author}'
draft: false
featured_image: "images/CUPFLB.png"
---
"""
    if text:
        post_content += f"\n{text}\n\n"
    if link:
        post_content += f"Visit the [link]({link})!\n"

    # Call the function to create a blog post on GitHub
    try:
        create_blog_post_and_image(post_content, dashed_title, current_datetime_formatted, image_folder, image_path)
        await ctx.respond(f'Blog post successfully sent and will be available momentarily at https://www.cupertino.forum/post/{dashed_title}-{current_datetime_formatted}/.')

        # Create and send the embed
        embed = discord.Embed(title=title, description=text, color=discord.Color.blue())
        embed.set_author(name=author)
        if header_image:
            embed.set_image(url=header_image)
        if link:
            embed.add_field(name="External Link", value=link, inline=False)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.respond(f'Failed to create blog post: {e}')

    # Delete the local post directory
    if os.path.isfile(image_folder) or os.path.isdir(image_folder):
        shutil.rmtree(image_folder)
        print(f"Successfully deleted {image_folder}")
    else:
        print(f"Failed to delete {image_folder}: {e}")

def download_image(url, path):
    try:
        response = requests.get(url)
        response.raise_for_status()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as file:
            file.write(response.content)
        print(f"Image downloaded successfully to {path}")
        return True  # Image downloaded successfully
    except Exception as e:
        print(f"Failed to download image: {e}")
        return False  # Image download failed

def create_blog_post_and_image(content, title, current_datetime_formatted, image_folder, image_path):
    safe_title = re.sub(r'[^a-zA-Z0-9\-]', '-', title.replace(' ', '-'))
    markdown_file_path = f'content/en/post/{safe_title}-{current_datetime_formatted}.md'
    
    # Push the markdown file to GitHub
    push_file(markdown_file_path, f"New blog post: {title}", content, BRANCH)

    # Add image file to the repository if it exists
    if os.path.exists(image_path):
        image_file_name = os.path.basename(image_path)
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        push_file(f'{image_folder}/{image_file_name}', f"Add image {image_file_name}", image_data, BRANCH)

def push_file(path, commit_message, content, branch, update=False):
    try:
        if update:
            contents = repo.get_contents(path, ref=branch)
            repo.update_file(contents.path, commit_message, content, sha=contents.sha, branch=branch)
        else:
            repo.create_file(path, commit_message, content, branch=branch)
    except Exception as e:
        print(f"Failed to push file: {e}")
        raise

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
