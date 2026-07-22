import { apiFetch } from './client'

export const getWallet  = () => apiFetch('/api/commerce/wallet/')
export const topUpWallet = (amount) =>
  apiFetch('/api/commerce/wallet/topup/', { method: 'POST', body: JSON.stringify({ amount }) })
export const getOrders  = () => apiFetch('/api/commerce/orders/')
export const redeemCoupon = (code) =>
  apiFetch('/api/commerce/coupons/redeem/', { method: 'POST', body: JSON.stringify({ code }) })

export const checkout = (courseIds) =>
  apiFetch('/api/commerce/checkout/', { method: 'POST', body: JSON.stringify({ course_ids: courseIds }) })
