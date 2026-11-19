import pytest
import os
from krita_mcp_lazy.animation.cinematic_video_renderer import (
    SweatParticleSystem,
    render_10s_animation_video,
)


def test_sweat_particle_system_dynamics():
    ps = SweatParticleSystem()
    # Emit droplets
    ps.emit(origin=(960, 400), count=5, base_speed=12.0)
    assert len(ps.particles) == 5
    
    # Step simulation
    ps.update(dt=1.0 / 24.0)
    assert len(ps.particles) == 5
    # Particles should travel leftward (opposing run direction)
    for p in ps.particles:
        assert p.x < 960


def test_short_video_render_smoke():
    out_path = "output/smoke_test_run.mp4"
    # Render 12 frames (0.5 second) for quick unit test
    res = render_10s_animation_video(
        output_mp4_path=out_path,
        total_frames=12,
        fps=24,
        width=640,
        height=360,
    )
    assert res["success"] is True
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) > 1000
