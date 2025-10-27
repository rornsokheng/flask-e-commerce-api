const { createApp } = Vue
createApp({
     delimiters: ['[[', ']]'],
     mounted() {
          let cart = JSON.parse(localStorage.getItem('cart_list') ?? '[]')
          this.cart_list = cart
          this.checkUserSession()
     },
     data() {
          return {
               message: 'Hello World!',
               counter: 0,
               cart_list: [],
               grand_total: 0,
               shipping_fee: 1.5,
               isLoggedIn: false,
               userEmail: '',

               customer: {
                    firstName: '',
                    lastName: '',
                    email: '',
                    phone: ''
               },
               address: {
                    street: '',
                    apartment: '',
                    city: '',
                    state: '',

               },
               payment: {
                    method: 'Bakong',

               },
               specialInstructions: '',
               tax_rate: 0.08
          }
     },
     methods: {
          async checkUserSession() {
               try {
                    const response = await axios.get('/api/check-session')
                    if (response.data.logged_in) {
                         this.isLoggedIn = true
                         this.userEmail = response.data.email
                         this.customer.email = response.data.email
                    }
               } catch (error) {
                    console.log('Not logged in or session check failed')
               }
          },

          handleSetItem(value) {
               console.log(value);
               localStorage.setItem('cart_list', JSON.stringify(value))
          },

          addToCart(product) {
               if (this.isLoggedIn) {
                    const existingProduct = this.cart_list.find(item => item.id === product.id)
                    if (existingProduct) {
                         existingProduct.qty += 1
                    } else {
                         const newProduct = { ...product, qty: 1 }
                         this.cart_list.push(newProduct)
                    }
                    this.handleSetItem(this.cart_list)
                    this.handleAlertSuccess({ title: 'Success!', description: 'Add to cart successfully.' });
               }else
                    window.location.href = "/login"
          },

          calGrandTotal() {
               this.grand_total = 0
               this.cart_list.forEach(item => {
                    let total = parseFloat(item.qty) * parseFloat(item.price)
                    this.grand_total += total
               })
               return this.grand_total
          },

          removeCart(index) {
               this.cart_list.splice(index, 1);
               this.handleSetItem(this.cart_list);
          },

          handleIncreaseCart(id) {
               const updatedCart = this.cart_list.map(item => {
                    if (item.id === id) {
                         return { ...item, qty: item.qty + 1 };
                    }
                    return item;
               });

               this.cart_list = updatedCart;
               this.handleSetItem(this.cart_list)
          },

          handleDecreaseCart(id) {
               const updatedCart = this.cart_list
                    .map(item => {
                         if (item.id === id && item.qty > 1) {
                              return { ...item, qty: item.qty - 1 };
                         } else if (item.id === id && item.qty <= 1) {
                              return null;
                         }
                         return item;
                    })
                    .filter(item => item !== null);

               this.cart_list = updatedCart;
               this.handleSetItem(this.cart_list)
          },

          handleAlertSuccess({ title = "Good job!", description = "You clicked the button!" } = {}) {
               return Swal.fire({
                    title: title,
                    text: description,
                    icon: "success"
               });
          },

          calTax() {
               return (this.calGrandTotal() * this.tax_rate).toFixed(2);
          },

          calOrderTotal() {
               return (parseFloat(this.calGrandTotal()) + parseFloat(this.shipping_fee) + parseFloat(this.calTax())).toFixed(2);
          },

          reqPostOrder: async function (payload) {
               const orderEndpoint = this.isLoggedIn
                    ? "http://127.0.0.1:5000/order-logged"
                    : "http://127.0.0.1:5000/order"

               return await axios
                    .post(orderEndpoint, payload)
                    .then((res) => {
                         return Promise.resolve(res.data);
                    })
                    .catch((err) => {
                         return Promise.reject(err)
                    })
          },

          submitOrder() {
               if (!this.customer.firstName || !this.customer.lastName || !this.customer.email || !this.customer.phone) {
                    Swal.fire({
                         title: 'Missing Information',
                         text: 'Please fill in all required contact information.',
                         icon: 'warning'
                    })
                    return;
               }

               const orderData = {
                    customer: this.customer,
                    address: this.address,
                    payment: this.payment,
                    items: this.cart_list,
                    specialInstructions: this.specialInstructions,
                    totals: {
                         subtotal: this.calGrandTotal(),
                         shipping: this.shipping_fee,
                         tax: this.calTax(),
                         total: this.calOrderTotal()
                    }
               };

               Swal.fire({
                    title: 'Processing Order...',
                    text: 'Please wait',
                    allowOutsideClick: false,
                    didOpen: () => {
                         Swal.showLoading()
                    }
               })

               this.reqPostOrder(orderData)
                    .then(() => {
                         Swal.close()
                         this.handleAlertSuccess({
                              title: "ការបញ្ជារទិញទទួលបានជោគជ័យ🙏",
                              description: this.isLoggedIn
                                   ? "សូមអរគុណ!!! ចូលមើលការបញ្ជាទិញរបស់អ្នកនៅក្នុង Profile"
                                   : "សូមអរគុណ!!!"
                         }).then(() => {
                              this.handleSetItem([])
                              window.location.href = this.isLoggedIn ? "/profile" : "/"
                         })
                    })
                    .catch((error) => {
                         Swal.close()
                         Swal.fire({
                              title: 'Error',
                              text: 'Failed to place order. Please try again.',
                              icon: 'error'
                         })
                         console.error('Order error:', error)
                    })
          },

          handlePlaceOrder() {
               if (this.cart_list.length === 0) {
                    window.location.href = "/"
               } else {
                    this.submitOrder()
               }
          },

          promptLogin() {
               Swal.fire({
                    title: 'Create an Account?',
                    text: 'Sign up to track your orders and get exclusive offers!',
                    icon: 'info',
                    showCancelButton: true,
                    confirmButtonText: 'Sign Up',
                    cancelButtonText: 'Continue as Guest'
               }).then((result) => {
                    if (result.isConfirmed) {
                         window.location.href = '/login'
                    }
               })
          }
     }

}).mount('#app')