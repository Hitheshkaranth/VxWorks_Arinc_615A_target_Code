// SPDX-License-Identifier: MPL-2.0
/**
 * @file
 * @copyright
 * This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
 * If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 * @author Thomas Vogt, thomas@thomas-vogt.de
 *
 * @brief Safe Cast Template.
 **/

#include <cstdint>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace ArincSupport {

template< typename TargetT, typename SourceT >
[[nodiscard]] constexpr TargetT safeCast( const SourceT source )
{
  static_assert( std::is_integral< TargetT >::value && std::is_integral< SourceT >::value,
    "safeCast requires integral types" );
  static_assert( std::is_convertible< SourceT, TargetT >::value, "safeCast requires convertible types" );
  if ( !inRange< TargetT >( source ) )
  {
    throw std::range_error{ "source value not in range of target type" };
  }

  return static_cast< TargetT >( source );
}

template<
  typename TargetT,
  TargetT min,
  TargetT max,
  typename SourceT >
constexpr bool inRange( const SourceT source ) noexcept
{
  static_assert( std::is_integral< TargetT >::value && std::is_integral< SourceT >::value,
    "inRange requires integral types" );
  bool representable{ false };
  if constexpr ( std::is_signed< SourceT >::value )
  {
    const auto value{ static_cast< std::intmax_t >( source ) };
    if constexpr ( std::is_signed< TargetT >::value )
    {
      representable = value >= static_cast< std::intmax_t >( std::numeric_limits< TargetT >::min() )
        && value <= static_cast< std::intmax_t >( std::numeric_limits< TargetT >::max() );
    }
    else
    {
      representable = value >= 0
        && static_cast< std::uintmax_t >( value ) <= static_cast< std::uintmax_t >( std::numeric_limits< TargetT >::max() );
    }
  }
  else
  {
    const auto value{ static_cast< std::uintmax_t >( source ) };
    representable = value <= static_cast< std::uintmax_t >( std::numeric_limits< TargetT >::max() );
  }
  return representable
    && ( static_cast< TargetT >( source ) >= min )
    && ( static_cast< TargetT >( source ) <= max );
}

}
