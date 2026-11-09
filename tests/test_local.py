# Copyright (c) 2026 Benjamin Cabé
# SPDX-License-Identifier: Apache-2.0

"""serve --local: a local branch reviewed as its pull request, from the merge base with the upstream branch."""

from __future__ import annotations

import argparse
import subprocess

import pytest
from mcp import Client

from zephyr_reviewer import mcp_server
from zephyr_reviewer.intel import SourceIntel
from zephyr_reviewer.intel.repo import merge_base, upstream_branch


def test_the_diff_starts_at_the_merge_base_with_upstream(local_clone):
    root = local_clone["root"]
    assert upstream_branch(root) == "origin/main"
    assert merge_base(root, "HEAD", "origin/main") == local_clone["base"]
    # The remote pointing at zephyrproject-rtos/zephyr wins, whatever it is called.
    subprocess.run(["git", "-C", root, "remote", "add", "zp", "https://github.com/zephyrproject-rtos/zephyr.git"])
    subprocess.run(["git", "-C", root, "update-ref", "refs/remotes/zp/main", local_clone["base"]])
    assert upstream_branch(root) == "zp/main"


async def test_review_prompt(local_clone):
    root = str(local_clone["root"])
    intel = SourceIntel(root, "HEAD", merge_base(root, "HEAD", "origin/main"))
    srv = mcp_server.build_server(intel)
    mcp_server.add_review_prompt(srv, intel, root, "HEAD", "origin/main")
    async with Client(srv) as client:
        assert [p.name for p in (await client.list_prompts()).prompts] == ["review"]
        text = (await client.get_prompt("review", {})).messages[0].content.text
    assert "## Change under review: feature" in text and "+int foo_recover(const struct device *dev)" in text
    assert "i2c_upstream.c" not in text and "There is no `submit_review` tool here" in text


def test_serve_needs_a_base_without_local():
    args = argparse.ArgumentParser()
    mcp_server.add_server_args(args)
    with pytest.raises(SystemExit, match="--base is required"):
        mcp_server.serve(args.parse_args([]))
