const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const BACKEND_ORIGIN =
  import.meta.env.VITE_BACKEND_URL ||
  (import.meta.env.VITE_API_BASE_URL
    ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1\/?$/, '')
    : '')

let accessToken = null

export function setAccessToken(token) {
  accessToken = token
}

export function mediaUrl(path) {
  if (!path) return ''

  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }

  if (path.startsWith('//')) {
    return window.location.protocol + path
  }

  if (BACKEND_ORIGIN) {
    return (
      BACKEND_ORIGIN.replace(/\/$/, '') +
      (path.startsWith('/') ? path : '/' + path)
    )
  }

  return path.startsWith('/') ? path : '/' + path
}

async function refreshAccessToken() {
  const response = await fetch(
    API_BASE + '/auth/token/refresh/',
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: '{}',
    }
  )

  if (!response.ok) {
    accessToken = null
    return false
  }

  const data = await response.json().catch(() => null)

  if (!data || !data.access) {
    accessToken = null
    return false
  }

  accessToken = data.access
  return true
}

export async function apiRequest(path, options = {}, canRefresh = true) {
  const headers = new Headers(options.headers || {})

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (accessToken) {
    headers.set('Authorization', 'Bearer ' + accessToken)
  }

  const response = await fetch(API_BASE + path, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (response.status === 401 && canRefresh) {
    const refreshed = await refreshAccessToken()

    if (refreshed) {
      return apiRequest(path, options, false)
    }
  }

  const data =
    response.status === 204
      ? null
      : await response.json().catch(() => null)

  if (!response.ok) {
    const error = new Error(
      data && data.detail
        ? data.detail
        : 'The request could not be completed.'
    )

    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

const api = {
  products: (query = '') =>
    apiRequest('/products/' + query),

  product: (slug) =>
    apiRequest('/products/' + encodeURIComponent(slug) + '/'),

  categories: () =>
    apiRequest('/categories/'),

  storeConfig: () =>
    apiRequest('/config/'),

  countries: () =>
    apiRequest('/countries/'),

  cart: () =>
    apiRequest('/cart/'),

  addToCart: (productId, quantity = 1) =>
    apiRequest('/cart/', {
      method: 'POST',
      body: JSON.stringify({
        product_id: productId,
        quantity: quantity,
      }),
    }),

  updateCartItem: (lineId, quantity) =>
    apiRequest('/cart/items/' + lineId + '/', {
      method: 'PATCH',
      body: JSON.stringify({
        quantity: quantity,
      }),
    }),

  removeCartItem: (lineId) =>
    apiRequest('/cart/items/' + lineId + '/', {
      method: 'DELETE',
    }),

  checkout: (payload) =>
    apiRequest('/checkout/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  posSearch: (term) =>
    apiRequest(
      '/pos/products/?search=' + encodeURIComponent(term)
    ),

  posSale: (payload) =>
    apiRequest('/pos/sales/create/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  posSales: () =>
    apiRequest('/pos/sales/'),

  posSaleDetail: (invoice) =>
    apiRequest(
      '/pos/sales/' + encodeURIComponent(invoice) + '/'
    ),

  correctPosSale: (invoice, payload) =>
    apiRequest(
      '/pos/sales/' +
        encodeURIComponent(invoice) +
        '/correction/',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),

  dashboard: () =>
    apiRequest('/reports/dashboard/'),

  login: (email, password) =>
    apiRequest(
      '/auth/token/',
      {
        method: 'POST',
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      },
      false
    ),

  register: (payload) =>
    apiRequest(
      '/auth/register/',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      false
    ),

  requestPasswordReset: (email) =>
    apiRequest(
      '/auth/password-reset/',
      {
        method: 'POST',
        body: JSON.stringify({
          email: email,
        }),
      },
      false
    ),

  confirmPasswordReset: (payload) =>
    apiRequest(
      '/auth/password-reset/confirm/',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      false
    ),

  me: () =>
    apiRequest('/auth/me/'),

  access: () =>
    apiRequest('/auth/access/'),

  logout: () =>
    apiRequest(
      '/auth/logout/',
      {
        method: 'POST',
      },
      false
    ),

  users: () =>
    apiRequest('/admin/users/'),

  createUser: (payload) =>
    apiRequest('/admin/users/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateUser: (id, payload) =>
    apiRequest('/admin/users/' + id + '/', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  sendContact: (payload) =>
    apiRequest(
      '/contact/',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      false
    ),
}

export {
  api,
  API_BASE,
  BACKEND_ORIGIN,
}
