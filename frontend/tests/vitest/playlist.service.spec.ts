import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as playlistService from '../../src/services/playlist'

beforeEach(() => {
  // reset mocks
  // @ts-ignore
  global.fetch = vi.fn()
})

describe('playlist service', () => {
  it('getPlaylist calls correct endpoint', async () => {
    // @ts-ignore
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => [{ id: '1', url: 'u' }] })
    const items = await playlistService.getPlaylist()
    // @ts-ignore
    expect(global.fetch).toHaveBeenCalled()
    expect(items).toBeInstanceOf(Array)
  })

  it('addTrack posts payload and returns created item', async () => {
    const payload = { url: 'http://example.com/song.mp3' }
    // @ts-ignore
    global.fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'new' }) })
    const res = await playlistService.addTrack(payload)
    // @ts-ignore
    expect(global.fetch).toHaveBeenCalled()
    expect(res.id).toBe('new')
  })
})
